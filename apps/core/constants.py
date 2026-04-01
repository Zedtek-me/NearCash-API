from apps.core.services import (
    GeoapifyService, OpenCageService,
    GoogleMapServices
)

LOCATION_SERVICES = {
    "geoapify": GeoapifyService,
    "opencage": OpenCageService,
    "google": GoogleMapServices
}

COUNTRY_CURRENCY_MAP = {
    "nigeria": "NGN",
    "ghana": "GHS",
    "kenya": "KES",
    "south africa": "ZAR",
    "united states": "USD",
    "united kingdom": "GBP",
    "canada": "CAD",
    "australia": "AUD",
    "european union": "EUR",
}

STORE_WALK_IN = "STORE_WALK_IN"
MEET_UP = "MEET_UP"
MEET_UP_AND_STORE_WALK_IN = "MEET_UP_AND_STORE_WALK_IN"

ACTIVE = "ACTIVE"
INACTIVE = "INACTIVE"
DELETED = "DELETED"
