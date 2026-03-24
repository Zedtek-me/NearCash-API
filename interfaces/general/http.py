from abc import ABC, abstractmethod


class HttpInterface(ABC):

    @abstractmethod
    def get(self, *args, **kwargs):
        raise NotImplementedError("GET method is not implemented on this instance!")

    @abstractmethod
    def post(self, *args, **kwargs):
        raise NotImplementedError("POST method is not implemented on this instance!")
