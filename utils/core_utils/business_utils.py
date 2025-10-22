from typing import Optional, Union, List, Type

from dateutil.relativedelta import relativedelta

from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance as Geodistance
from django.db.models import Q, Sum, QuerySet, Case, When, Value, FloatField, F
from django.db.models.functions import Cast
from django.utils import timezone

from apps.auths.models import User
from apps.core.models import (
    Business, BusinessTransactionPolicy,
    BusinessClientCategory, BusinessClient,
    CurrentLocation
)

from apps.core.services import ClientService


from apps.core.constants import LOCATION_SERVICES
from apps.wallet.models import Transaction
from apps.wallet.constants import FULFILLED

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException

from utils.core_utils.location_utils import GeolocationUtils
from utils.core_utils.core_utils import CoreUtil
from utils.wallet_utils.transactions import TransactionUtil

from dtos.core_dtos.business_dtos import UpdateBusinessDto

class BusinessUtil:

    @classmethod
    def create_business(
        cls, user: User, data: dict
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
        cls, current_lat: float, current_long: float, radius: int = 2000
    ) -> List[Business]:
        """returns all the businesses that are within a radius of the current location"""
        point = Point(current_long, current_lat, srid=4326)
        businesses = Business.objects.annotate(
            distance=Geodistance("geo_location", point)
        ).filter(
            geo_location__distance_lte=(point, radius)
        ).order_by("distance")
        return businesses

    @classmethod
    def get_business(
        cls, filter_params: dict
    ) -> Business:
        return Business.objects.filter(**filter_params).first()

    @classmethod
    def get_businesses(
        cls, user: Type["User"], data: dict
    ) -> List[Business]:
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
            **filter_params
        )
        return businesses

    @classmethod
    def update_business(
        cls, business: Business, data: Union[UpdateBusinessDto, dict]
    )-> Optional[Business]:
        """updates a business"""
        updated_address = None
        for field, value in data.items():
            if hasattr(business, field) and value is not None:
                if field == "address":
                    updated_address = value
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
        business.save()
        return business

    @classmethod
    def fetch_business_txn_policy_for_current_client(
        cls, client: User, business_id: Union[int, str]
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
        cls, client: User, data: dict,
    ) -> Transaction:
        """client initiates transaction to a vendor"""
        txn = ClientService.initiate_transaction(client, data)
        return txn


    @classmethod
    def get_vendor_latest_location(
        cls,  vendor_id: Union[str, int],
        client_coordinate: Optional[dict] = None
    ) -> dict:
        """
        fetches the current location of a vendor
        in order to display to the end user on the map
        """

        from apps.core.models import CurrentLocation

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
        cls, user: User, location: dict, location_type: str = "Vendor",
        **kwargs
    ) -> CurrentLocation:
        """
        captures the current location of a user either vendor or client
        """
        business = None
        if location_type.title() == "Vendor":
            business = cls.get_business({"id": kwargs.get("business_id")})

        loc = CurrentLocation(
            user=user,
            location=Point(location.get("longitude"), location.get("latitude"), srid=4326),
            location_type=location_type.title(),
            business=business
        )
        loc.save()
        return loc

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
        logger.debug(f"extra charges on all transactions")
        return extra_charge_val or 0.0
