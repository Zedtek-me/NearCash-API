from abc import ABC, abstractmethod



class SMSInterface(ABC):

    @classmethod
    @abstractmethod
    def send(
        cls, content: dict | str | int | float,
        recipient_ids: list
    ) -> bool:
        """
        sends ${content} to ${recipient_ids}
        """
