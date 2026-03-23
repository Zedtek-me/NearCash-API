from abc import ABC, abstractmethod


class PaymentInterface(ABC):

    @classmethod
    @abstractmethod
    def get_virtual_account(cls, *args, **kwargs):
        raise NotImplementedError(f"{PaymentInterface.get_virtual_account.__name__} not implemented!")

    @classmethod
    @abstractmethod
    def initiate_payout(cls, *args, **kwargs):
        raise NotImplementedError(f"{PaymentInterface.get_virtual_account.__name__} not implemented!")