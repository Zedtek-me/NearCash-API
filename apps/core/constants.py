from apps.core.services import GeoapifyService, OpenCageService

LOCATION_SERVICES = {
    "geoapify": GeoapifyService,
    "opencage": OpenCageService,
    "google": None
}

STORE_WALK_IN = "STORE_WALK_IN"
MEET_UP = "MEET_UP"
MEET_UP_AND_STORE_WALK_IN = "MEET_UP_AND_STORE_WALK_IN"

ACTIVE = "ACTIVE"
INACTIVE = "INACTIVE"
DELETED = "DELETED"
