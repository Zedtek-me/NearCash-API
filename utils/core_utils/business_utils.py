from typing import Optional, Union, List, Type

from dateutil.relativedelta import relativedelta

from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance as Geodistance
from django.db.models import (
     Q, Sum, QuerySet, Case, When, Value, FloatField, F,
     ExpressionWrapper, BooleanField, Subquery
)
from django.db.models.functions import Cast
from django.utils import timezone
from django.db import transaction

from apps.core.models import (
    Business, BusinessTransactionPolicy,
    BusinessClientCategory, BusinessClient,
    CurrentLocation
)

from apps.core.services import ClientService
from apps.core.schema.types.client_types import DelayedTransactionResponseInputType
from apps.auths.models import User

from apps.core.constants import LOCATION_SERVICES
from apps.wallet.models import Transaction, TransactionOpportunity
from apps.wallet.constants import FULFILLED, CANCELLED, IN_PROGRESS

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException

from utils.core_utils.location_utils import GeolocationUtils
from utils.core_utils.core_utils import CoreUtil
from utils.wallet_utils.transactions import TransactionUtil
from utils.notifications.notifications import NotificationUtil
from utils.helpers.kwargs import KwargUtil

from dtos.core_dtos.business_dtos import UpdateBusinessDto
from background_tasks.core.business import BusinessAsyncOperations

class BusinessUtil:

    @classmethod
    def create_business(
        cls, user, data: dict
    ) -> Business:
        """creates a vendor business"""

        country = data.get("country", "").title()
        # TODO: use a mapping of countries and their currencies plus country code
        # in order to update currency, in case none is provided
        if not user.businesses.exists():
            data["is_primary"] = True
        business = Business.objects.create(owner=user, **data)
        country_code = "ng"
        if country == "Nigeria":
            business.currency = "NGN"
        business.save()
        google_service = LOCATION_SERVICES.get("google")
        coordinates = GeolocationUtils(google_service).get_coordinate(
            business.address, country_code=country_code
        )
        logger.debug(f"Coordinates for business {business.name}: {coordinates}")
        business.geo_location = Point(
            coordinates.get("longitude", 0),
            coordinates.get("latitude", 0), srid=4326
        )
        business.save()
        # default business txn policy -- it can be editable by the business later.
        CoreUtil.create_business_txn_policy(
            business, {"name": "general"}
        )
        return business

    @classmethod
    def get_nearby_businesses(
        cls, current_lat: float, current_long: float, radius: int = 3000
    ) -> QuerySet:
        """returns all the businesses that are within a radius of the current location"""
        point = Point(current_long, current_lat, srid=4326)
        businesses_in_defined_km = Business.objects.none()
        businesses_away_from_user = Business.objects.annotate(distance=Geodistance("geo_location", point))
        # resolution 3km, 5km, and or 15km
        # 3km first
        businesses_in_defined_km = businesses_away_from_user.filter(
            geo_location__distance_lte=(point, radius)
        )
        # 5km next
        if not businesses_in_defined_km or businesses_in_defined_km.count() < 3:
            radius = 5000
            businesses_in_defined_km = businesses_away_from_user.filter(
                geo_location__distance_lte=(point, radius)
            )
        # 15km last
        if not businesses_in_defined_km or businesses_in_defined_km.count() < 3:
            radius = 15000
            businesses_in_defined_km = businesses_away_from_user.filter(
                geo_location__distance_lte=(point, radius)
            )
        nearest_business = businesses_in_defined_km.values("distance").first() or {}
        businesses = businesses_in_defined_km.annotate(
                nearest=Case(
                    When(distance=nearest_business.get("distance"), then=Value(True)),
                    default=False,
                    output_field=BooleanField()
                )
        )
        # order by liquidity availability first, then distance
        businesses = businesses.order_by("-available_liquidity").order_by("distance")
        return businesses

    @classmethod
    def get_business(
        cls, filter_params: dict
    ) -> Business:
        return Business.objects.filter(**filter_params).first()

    @classmethod
    def get_businesses(
        cls, user: Type["User"], data: dict, search: Q = Q()
    ) -> QuerySet:
        """returns all the businesses for a user"""
        filter_params = {"owner": user}
        if data.get("id"):
            filter_params["id"] = data["id"]
        if data.get("owner_id"):
            del filter_params["owner"]
            filter_params["owner__id"] = data["owner_id"]
        if data.get("name"):
            filter_params["name__icontains"] = data["name"]
        if data.get("address"):
            filter_params["address__icontains"] = data["address"]

        businesses = Business.objects.filter(
            search,
            **filter_params
        )
        return businesses

    @classmethod
    def update_business(
        cls, business: Business, data: Union[UpdateBusinessDto, dict],
        financial_assets: Optional[List[dict]] = None
    )-> Optional[Business]:
        """updates a business"""
        from utils.wallet_utils.wallet import WalletUtil

        updated_address = None
        explicit_business_online_status = False
        for field, value in data.items():
            if hasattr(business, field) and value is not None:
                if field == "address":
                    updated_address = value
                if field == "is_online":
                    explicit_business_online_status = value
                setattr(business, field, value)
        if updated_address:
            google_service = LOCATION_SERVICES.get("google")
            # TODO: dynamically get country code based on the business' current country
            coordinates = GeolocationUtils(google_service).get_coordinate(
                updated_address, country_code="ng"
            )
            business.geo_location = Point(
                coordinates.get("longitude", 0),
                coordinates.get("latitude", 0), srid=4326
            )
        if explicit_business_online_status:
            business.meta["explicit_online_status"] = explicit_business_online_status
        business.save()
        if financial_assets is not None:
            WalletUtil.create_or_update_financial_assets(
                business, financial_assets
            )
        return business

    @classmethod
    def fetch_business_txn_policy_for_current_client(
        cls, client, business_id: Union[int, str]
    ) -> Optional[BusinessTransactionPolicy]:
        """
        checks if the current client is added to any
        category first, in order to determine the suitable
        policy to use for the current client's txn.
        if client doesn't belong to any business txn category,
        the default txn policy for the business is used
        """
        if existing_business_client := BusinessClient.objects.filter(
            (
                Q(category__business__id=business_id) |
                Q(business__id=business_id)
            ), client=client
        ).first():
            return (
                existing_business_client.category and
                existing_business_client.category.txn_policy
            ) or CoreUtil.fetch_business_txn_policy(business_id, {"name__iexact": "general"})
        return CoreUtil.fetch_business_txn_policy(
            business_id, {"name__iexact": "general"}
        )

    @classmethod
    def initiate_transaction(
        cls, client, data: dict,
    ) -> Transaction:
        """client initiates transaction to a vendor"""
        txn = ClientService.initiate_transaction(client, data)
        return txn


    @classmethod
    def get_vendor_latest_location(
        cls,  **query_data: dict
    ) -> dict:
        """
        fetches the current location of a vendor
        in order to display to the end user on the map
        """

        from apps.core.models import CurrentLocation
        from apps.auths.models import User

        vendor_id = query_data.get("vendor_id")
        txn_id = query_data.get("txn_id")
        client_coordinate = None
        txn = TransactionUtil.get_transaction(**{"id": txn_id})
        if txn:
            client_coordinate = {
                "longitude": txn.meta.get("client_current_location", {}).get("longitude"),
                "latitude": txn.meta.get("client_current_location", {}).get("latitude")
            }
        vendor_user = User.objects.filter(id=vendor_id, meta__user_type="VENDOR").first()
        if not vendor_user:
            return {}
        current_location: CurrentLocation = vendor_user.current_locations.first() #default ordering is by -date_created
        if not current_location:
            return {}
        vendor_location = {
            "latitude": current_location.location.y,
            "longitude": current_location.location.x,
        }

        if client_coordinate:
            point1 = (
                client_coordinate.get("latitude"),
                client_coordinate.get("longitude")
            )

            point2 = (
                vendor_location.get("latitude"),
                vendor_location.get("longitude")
            )
            vendor_location["distance_from_client"] = GeolocationUtils.calculate_distance(
                point1, point2
            )
        return vendor_location

    @classmethod
    def record_current_location(
        cls, user, location: dict, location_type: str = "Vendor",
        **kwargs
    ) -> CurrentLocation:
        """
        captures the current location of a user either vendor or client
        """
        business = None
        if location_type.title() == "Vendor":
            business = cls.get_business({"id": kwargs.get("business_id")})
        loc = cls.fetch_existing_user_location(
            user=user,
            location_type=location_type.title(),
            business=business
        )
        if loc:
            loc.location = Point(location.get("longitude"), location.get("latitude"), srid=4326)
        else:
            loc = CurrentLocation(
            user=user,
            location=Point(location.get("longitude"), location.get("latitude"), srid=4326),
            location_type=location_type.title(),
            business=business
        )
        loc.save()
        return loc

    @classmethod
    def fetch_existing_user_location(
        cls, user, **kwargs
    ) -> Optional[CurrentLocation]:
        return user.current_locations.filter(**kwargs).first()

    @classmethod
    def get_txn_analytics(
        cls, user, user_type: str, business_id: Optional[str] = None
    ) -> dict:
        """
        returns the transaction analytics for a business
        """
        if user_type and user_type.lower() not in ["vendor", "client"]:
            raise CustomException("Please specify whether vendor or client analytics to retrieve!")

        if user_type.lower() == "vendor" and not business_id:
            raise CustomException(
                "Please specify the business whose analytics needs to be retreived!"
            )

        now = timezone.now()
        past_month_date = now - relativedelta(months=1)
        txn_analytics = {
            "total_transactions": 0,
            "fulfilled_trasactions": 0,
            "current_month_transactions": 0,
            "total_transaction_value": 0.0,
            "current_month_transaction_value": 0.0,
            "percentage_reduction_from_past_month": 0.0,
            "total_charges_plus_extra": 0.0,
            "extra_charges": 0.0
        }

        if user_type.lower() == "vendor":
            total_trxns = Transaction.objects.filter(
                vendor__id=user.id, business_id=business_id
            )
        else:
            total_trxns = Transaction.objects.filter(
                client__id=user.id
            )
        fulfilled_trxns = total_trxns.filter(status=FULFILLED)
        current_month_trxns = fulfilled_trxns.filter(
            date_created__date__year=now.date().year,
            date_created__date__month=now.month,
        )
        past_month_trxns = fulfilled_trxns.filter(
            date_created__date__year=past_month_date.year,
            date_created__month=past_month_date.month
        )

        current_month_trxn_value = current_month_trxns.aggregate(curr_month_val=Sum("amount")).get("curr_month_val") or 0.0
        past_month_trxn_value = past_month_trxns.aggregate(past_month_val=Sum("amount")).get("past_month_val") or 0.0
        total_trxns_value = fulfilled_trxns.aggregate(trxn_value=Sum("amount")).get("trxn_value") or 0.0
        total_charges = fulfilled_trxns.aggregate(total_charges=Sum("charge")).get("total_charges") or 0.0
        extra_charges_sum = cls._sum_extra_charges_on_trxns(fulfilled_trxns)
        total_charges += extra_charges_sum

        txn_analytics.update({
            "total_transactions": total_trxns.count(),
            "fulfilled_transactions": fulfilled_trxns.count(),
            "current_month_transactions": current_month_trxns.count(),
            "total_transaction_value": total_trxns_value,
            "current_month_transaction_value": current_month_trxn_value,
            "total_charges_plus_extra": total_charges,
            "extra_charges": extra_charges_sum
        })
        if past_month_trxn_value > current_month_trxn_value:
            percentage_reduction = (
                current_month_trxn_value / past_month_trxn_value
            ) * 100
            txn_analytics["percentage_reduction_from_past_month"] = percentage_reduction
        return txn_analytics

    @classmethod
    def _sum_extra_charges_on_trxns(
        cls, trxns: QuerySet
    ) -> float:
        """
        aggregates all of the extra charges on each transaction object
        """
        extra_charge_val = trxns.filter(
            extra_charge__has_key="amount"
        ).aggregate(extra_charge_val=Sum(Cast("extra_charge__amount", output_field=FloatField())))\
            .get("extra_charge_val")
        return extra_charge_val or 0.0

    @classmethod
    def get_client_latest_location(
        cls, **query_data: dict
    ) -> Union[CurrentLocation, dict]:
        from apps.core.models import BusinessClient

        client_id = query_data.get("client_id")
        trxn_id = query_data.get("txn_id")
        trxn = TransactionUtil.get_transaction(**{"id": trxn_id})
        vendor_business_id = trxn and trxn.business.id
        buz_client = BusinessClient.objects.filter(
            client__id=client_id, business__id=vendor_business_id
        ).first()

        if not buz_client:
            logger.debug(
                f"could not find client user with id: {client_id} "
                f"for transaction business: {vendor_business_id}"
            )
            return {}
        client = buz_client and buz_client.client
        client_latest_loc: CurrentLocation | None = client.current_locations.first()
        if not client_latest_loc:
            return {}
        return {
            "longitude": client_latest_loc.location.x,
            "latitude": client_latest_loc.location.y
        }

    @classmethod
    def record_vendor_location(
        cls, **content: dict
    ) -> dict:
        from apps.auths.models import User

        vendor_id = content.get("vendor_id")
        business_id = content.get("business_id")
        location = content.get("location")
        trxn_id = content.get("txn_id")

        business = cls.get_business({"id": business_id})
        trxn: Union[Transaction, None] = TransactionUtil.get_transaction(**{"id": trxn_id})
        if (not business_id or not business) and trxn:
            business = trxn and trxn.business
        if not location or not business:
            raise CustomException("Invalid data provided for recording location")
        vendor_id = vendor_id or (business and business.owner.id)
        vendor_user = User.objects.filter(id=vendor_id, meta__user_type="VENDOR").first()
        location = cls.record_current_location(
            vendor_user, location, location_type="Vendor",
            business_id=business_id
        )
        return location

    @classmethod
    def record_client_location(
        cls, **content: dict
    ) -> dict:
        from apps.core.models import BusinessClient
        from apps.auths.models import User

        [
            client_id, location
        ] = KwargUtil.cherry_pick_data(
            content, ["client_id", "location"]
        )

        if not (client_id and location):
            raise CustomException("Invalid data provided for recording location")
        client_user = User.objects.filter(id=client_id, meta__user_type="CLIENT").first()

        location = cls.record_current_location(
            client_user, location, "Client"
        )
        return location

    @classmethod
    def get_vendor_client_users(
        clse, user, data: dict
    ) -> QuerySet:
        """
        returns a list of all the clients that have patronized the given vendor
        """
        from apps.auths.models import User

        vendor_id = data.get("vendor_id")
        category_id = data.get("category_id")
        business_id = data.get("business_id")
        _filter = {"business__owner__id": vendor_id, "business_id": business_id}
        if category_id:
            _filter["category_id"] = category_id
        buz_client_ids = BusinessClient.objects.filter(**_filter)\
            .order_by("client_id")\
            .distinct("client_id")\
            .values_list("client_id", flat=True)
        buz_client_users = User.objects.filter(id__in=buz_client_ids)
        return buz_client_users

    @classmethod
    def get_vendor_users(
        cls, user, data: dict
    ) -> QuerySet:
        """
        returns vendors that the given user has patronized as a client
        """
        from apps.auths.models import User

        is_client = user.meta.get("user_type", "") == "CLIENT"
        vendor_id = data.get("vendor_id")
        search = data.get("search")

        search_filter = Q()

        if not is_client:
            raise CustomException("Only client can fetch all vendor's they've patronized!")
        trxns = user.client_transactions.all()
        if vendor_id:
            trxns = trxns.filter(vendor_id=vendor_id)
        trxn_vendor_ids = trxns.values_list("vendor_id", flat=True)
        if search:
            search_filter = (
                Q(email__icontains=search) |
                Q(username__icontains=search) |
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search)
            )
        vendors_users = User.objects.filter(search_filter, id__in=trxn_vendor_ids)
        return vendors_users

    @classmethod
    def get_vendor_businesses(
        cls, user, data: dict, search: Q = Q()
    ) -> QuerySet:
        """
        returns the businesses of the vendors that the given user has patronized as a client
        """
        from apps.auths.models import User

        is_client = user.meta.get("user_type", "") == "CLIENT"
        business_id = data.get("business_id")
        vendor_id = data.get("vendor_id")
        search = data.get("search")

        search_filter = Q()

        if not is_client:
            raise CustomException("Only client can fetch all vendor's they've patronized!")
        trxns = user.client_transactions.all()
        if business_id:
            trxns = trxns.filter(business_id=business_id)
        trxn_business_ids = trxns.values_list("business_id", flat=True)
        if search:
            search_filter = Q(name__icontains=search) | Q(address__icontains=search)
        if vendor_id:
            search_filter &= Q(owner__id=vendor_id)
        vendor_businesses = Business.objects.filter(search_filter, id__in=trxn_business_ids)
        return vendor_businesses


    @classmethod
    def check_and_activate_vendor_businesses(
        cls, user: User, _all: Optional[bool] = False,
        business_id: Union[None, str, int] = None,
        skip_error: Optional[bool] = False
    ) -> None:
        """
        sets the vendor businesses to active when they're logged in, and connected to websocket
        """
        user_type = user.meta.get("user_type", "").upper()
        not_a_vendor = user_type != "VENDOR"

        if not_a_vendor and not skip_error:
            raise CustomException("You're not allowed to perform this action!")
        if not_a_vendor:
            return

        if not _all and not business_id:
            raise CustomException(
                "Please specify the business to activate or "
                "set _all to true to activate all businesses!"
            )
        #so we don't automatically turn on a business the vendor explicitly turned offline previously.
        search_filter = (
            ~Q(meta__has_key="explicit_online_status") |
            Q(meta__has_key="explicit_online_status", meta__explicit_online_status=True)
        )
        businesses = Business.objects.none()
        if business_id:
            businesses = cls.get_businesses(user, {"id": business_id}, search_filter)
            if not businesses or not businesses.first():
                raise CustomException("Business with the provided id does not exist!")
        else:
            businesses = cls.get_businesses(user, {"owner": user}, search_filter)
        businesses.update(is_online=True)


    @classmethod
    def deactivate_businesses_for_vendor(
        cls, user: User, _all: Optional[bool] = False,
        business_id: Union[None, str, int] = None, skip_error: Optional[bool] = False
    ) -> None:
        """
        sets the vendor businesses to offline when they're logged out, and disconnected from websocket
        """
        user_type = user.meta.get("user_type", "").upper()
        not_a_vendor = user_type != "VENDOR"

        if not_a_vendor and not skip_error:
            raise CustomException("You're not allowed to perform this action!")

        if not_a_vendor:
            return

        if not _all and not business_id:
            raise CustomException(
                "Please specify the business to deactivate or "
                "set _all to true to deactivate all businesses!"
            )
        businesses = Business.objects.none()
        if business_id:
            businesses = cls.get_businesses(user, {"id": business_id})
            if not businesses or not businesses.first():
                raise CustomException("Business with the provided id does not exist!")
        else:
            businesses = cls.get_businesses(user, {"owner": user})
        businesses.update(is_online=False)


    @classmethod
    def handle_delayed_trxn_response(
        cls, client: User, response_data: dict | DelayedTransactionResponseInputType
    ) -> bool:
        """
        handle the response of a client user
        regarding his delayed transaction response
        """
        acceptable_decisions = [
            "wait_on_vendor",
            "system_search",
            "cancel"
        ]
        trxn_id = response_data.get("txn_id")
        decision = response_data.get("decision")
        decision = decision.value
        logger.debug(f"decision::::: {decision}")
        if decision not in acceptable_decisions:
            raise CustomException(
                message=f"invalid decision!"
            )
        trxn = TransactionUtil.get_transaction(id=trxn_id)
        if not trxn:
            raise CustomException(
                message=f"invalid transaction id: {trxn_id}"
            )

        match decision:
            case "system_search":
                # handle system auto-search
                # for other nearer vendors who can deliver the given cash
                cls.validate_and_broadcast_request_to_vendors(trxn)

            case "wait_on_vendor":
                # prompt the vendor again for this transaction
                NotificationUtil.send_socket_notification(trxn, skip_record=True)
                BusinessAsyncOperations.other_vendor_transaction_notif.delay(txn_id=trxn.id)

            case "cancel":
                TransactionUtil.update_txn_status(client, {"status": CANCELLED})
            case _:
                return True
        return True


    @classmethod
    def validate_and_broadcast_request_to_vendors(
        cls, trxn: Transaction
    ):
        """
        checks that all or any vendor in the list has the requested amount;
        then send a notification to the vendor(s) about the trxn.
        """
        BusinessAsyncOperations.notify_vendors_about_trxn_opportunity.delay(
            trxn_id=trxn.id
        )


    @classmethod
    def register_opportunity_for_business(
        cls, trxn: Transaction, business: Business
    ) -> TransactionOpportunity:
        """
        captures the transaction interest as an opportunity
        for the given business.
        """
        return TransactionOpportunity.objects.create(
            business=business, transaction=trxn
        )


    @classmethod
    def accept_transaction_opportunity(
        cls, **data: dict
    ) -> bool:
        """
        locks trxn for a vendor who just accepted an opportunity
        """
        with transaction.atomic():
            trxn_id, trxn_ref = data.get("txn_id"), data.get("txn_ref")
            vendor_business_id = data.get("business_id")
            vendor_who_accepted_transaction = cls.get_business({"id": vendor_business_id})
            if not vendor_who_accepted_transaction:
                raise CustomException(
                    message=f"couldn't find vendor with id: {vendor_business_id}"
                )
            trxn = Transaction.objects.select_for_update().filter(
                id=trxn_id, txn_ref=trxn_ref
            ).first()
            if not trxn:
                raise CustomException(
                    f"couldn't find a transaction with id: {trxn_id} and ref: {trxn_ref}!"
                )
            if trxn.status == IN_PROGRESS:
                return False
            trxn.status = IN_PROGRESS
            trxn.vendor = vendor_who_accepted_transaction.owner
            trxn.business = vendor_who_accepted_transaction
            trxn.save()

        transaction.on_commit(
            lambda: BusinessAsyncOperations.run_post_opportunity_acceptance_task.delay(
                trxn_id=trxn.id
            )
        )
        return True
