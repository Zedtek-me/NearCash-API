from apps.core.services import (
    GeoapifyService, OpenCageService,
    GoogleMapServices
)

LOCATION_SERVICES = {
    "geoapify": GeoapifyService,
    "opencage": OpenCageService,
    "google": GoogleMapServices
}

STORE_WALK_IN = "STORE_WALK_IN"
MEET_UP = "MEET_UP"
MEET_UP_AND_STORE_WALK_IN = "MEET_UP_AND_STORE_WALK_IN"

ACTIVE = "ACTIVE"
INACTIVE = "INACTIVE"
DELETED = "DELETED"
