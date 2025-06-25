from interfaces.general.location import LocationInterface

class GeolocationUtils:

    def __init__(self, geolocation_service: LocationInterface) -> None:
        self.geolocation_service = geolocation_service

    def get_coordinate(self, address: str) -> dict:
        """
        Fetches the coordinates (latitude and longitude) for a given address.
        Returns a dictionary with 'latitude' and 'longitude'.
        """
        return self.geolocation_service.get_coordinate(address)
