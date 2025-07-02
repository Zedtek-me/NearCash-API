from typing import Optional, Union, List, Type

from django.contrib.gis.geos import Point
from django.contrib.gis.db.models.functions import Distance as Geodistance

from apps.auths.models import User
from apps.core.models import Business
from apps.core.constants import LOCATION_SERVICES

from utils.helpers.logs import logger
from utils.core_utils.location_utils import GeolocationUtils

class BusinessUtil:

    @classmethod
    def create_business(
        cls, user: User, data: dict
    ) -> Business:
        """creates a vendor business"""

        country = data.get("country", "").title()
        # TODO: use a mapping of countries and their currencies plus country code
        # in order to update currency, in case none is provided
        # Also, get the coordinate of the business address and save in the _location column
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
        # TODO: if for some reasons no coordinate is gotten from this service, we should rotate our geo providers
        business._location = Point(
            coordinates.get("longitude", 0),
            coordinates.get("latitude", 0), srid=4326
        )
        business.save()
        return business

    @classmethod
    def get_nearby_businesses(
        cls, current_lat: float, current_long: float, radius: int = 2000
    ) -> List[Business]:
        """returns all the businesses that are within a radius of the current location"""
        point = Point(current_long, current_lat, srid=4326)
        businesses = Business.objects.annotate(
            distance=Geodistance("_location", point)
        ).filter(
            _location__distance_lte=(point, radius)
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
