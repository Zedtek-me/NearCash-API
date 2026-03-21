from django.db.models.signals import post_save
from .models import Transaction
from .constants import CANCELLED

from utils.helpers.general import generate_unique_id


def optionally_return_liquidity(
    sender: Transaction,
    instance: Transaction,
    updated: bool = False,
    **kwargs
):
    """
    checks whether the currently saved transaction
    was cancelled; if so, it returns back its liquidity to the
    business availale liquidity
    """
    from background_tasks.core.business import BusinessAsyncOperations

    if updated and instance.status == CANCELLED and not instance.meta.get("liquidity_returned"):
        BusinessAsyncOperations.return_transaction_amount_to_vendor_available_liquidity(
            instance.business, instance
        )


post_save.connect(optionally_return_liquidity, sender=Transaction, dispatch_uid=generate_unique_id())
