from typing import Optional, Union, List, Type

from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance as Geodistance
from django.db.models import Q

from apps.auths.models import User
from apps.core.models import (
    Business, BusinessTransactionPolicy,
    BusinessClientCategory, BusinessClient
)

from apps.core.services import ClientService


from apps.core.constants import LOCATION_SERVICES
from apps.wallet.models import Transaction

from utils.helpers.logs import logger
from utils.core_utils.location_utils import GeolocationUtils
from utils.core_utils.core_utils import CoreUtil

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
        business = Business.objects.create(owner=user, **data)
        country_code = "ng"
        if country == "Nigeria":
            business.currency = "NGN"
        business.save()
        geoapify_service = LOCATION_SERVICES.get("geoapify")
        coordinates = GeolocationUtils(geoapify_service).get_coordinate(
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
            geoapify_service = LOCATION_SERVICES.get("geoapify")
            # TODO: dynamically get country code based on the business' current country
            coordinates = GeolocationUtils(geoapify_service).get_coordinate(
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
