from typing import Type, Callable, Optional

from interfaces.general.location import LocationInterface

class GeolocationUtils:

    def __init__(self, geolocation_service: Type[LocationInterface]) -> None:
        self.geolocation_service = geolocation_service

    def get_coordinate(self, address: str, country_code: str) -> dict:
        """
        Fetches the coordinates (latitude and longitude) for a given address.
        Returns a dictionary with 'latitude' and 'longitude'.
        """
        return self.geolocation_service.get_coordinate(address, country_code)

    def get_routes(
        self, start_coord: dict, end_coord: Optional[dict],
        business: Optional[Type["Business"]], mode: Optional[str] = "walk"
    ) -> Optional[dict]:
        """gets routes between two waypoints"""
        return self.geolocation_service.get_routes(
            start_coord=start_coord,
            end_coord=end_coord,
            business=business,
            mode=mode
        )
