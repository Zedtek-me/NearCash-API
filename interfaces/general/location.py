from abc import ABC, abstractmethod
from typing import Optional, Union, Type

class LocationInterface(ABC):

    @classmethod
    @abstractmethod
    def get_coordinate(cls, address: str, country_code: str) -> dict:
        """
        Fetches the coordinates (latitude and longitude) for a given address.
        Returns a dictionary with 'latitude' and 'longitude'.
        """
        raise NotImplementedError("Method get_coordinate not implemented!")

    @classmethod
    @abstractmethod
    def get_routes(
        cls, start_coord: dict, end_coord: Optional[dict] = None,
        business: Optional[Type["Business"]] = None, mode: Optional[str] = "walk"
    ) -> dict:
        """returns routes between two waypoints"""
        raise NotImplementedError("Method get_routes not implemented!")
