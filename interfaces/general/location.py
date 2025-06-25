from abc import ABC, abstractmethod


class LocationInterface(ABC):

    @classmethod
    @abstractmethod
    def get_coordinate(cls, address: str, country_code: str) -> dict:
        """
        Fetches the coordinates (latitude and longitude) for a given address.
        Returns a dictionary with 'latitude' and 'longitude'.
        """
        raise NotImplementedError("Method get_coordinate not implemented!")
