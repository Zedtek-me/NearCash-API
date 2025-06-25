from typing import Optional, Union, List

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
        # TODO: if for some reasons no coordinate is gotten from this service, we shoulld rotate our geo providers
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
        logger.debug(f"Found {len(businesses)} businesses within {radius} meters of the given coordinates.")
        return businesses
