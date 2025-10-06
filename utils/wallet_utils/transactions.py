import uuid

from django.db.models import Q

from apps.wallet.models import Transaction
from utils.helpers.exception import CustomException

from apps.wallet.constants import (
    IN_PROGRESS, CANCELLED,
    FULFILLED, TXN_STATUSES
)

class TransactionUtil:
    """all things txn related"""

    @classmethod
    def generate_txn_reference(cls, prefix: str = "NCSH") -> str:
        """generates a unique transaction reference"""
        return f"{prefix}-{uuid.uuid4().hex[:8].upper()}"

    @classmethod
    def create_transaction(
        cls, **txn_data: dict
    ) -> Transaction:
        """records and returns a transaction"""
        return Transaction.objects.create(**txn_data)

    @classmethod
    def get_transaction(
        cls, only_one: bool = True, search_filter: Q = Q(),
        **_filter
    ) -> Transaction:
        txns = Transaction.objects.filter(search_filter, **_filter).select_related(
            "client", "vendor", "asset", "business"
        )
        if only_one:
            return txns.first()
        return txns

    @classmethod
    def update_txn_status(
        cls, user, data
    ) -> Transaction:
        """
        updates txn status and publish notification accordingly, if needed --
        depending on the status type.
        """
        from background_tasks.core.business import BusinessAsyncOperations

        txn = cls.get_transaction(
            id=data.get("txn_id"), only_one=True
        )
        if not txn:
            raise CustomException("Transaction not found.")

        status = data.get("status", "")
        if status and not isinstance(status, str):
            status = status.value.upper()

        if status == IN_PROGRESS and user.id != txn.vendor.id:
            raise CustomException(
                "Only the vendor can update the transaction to IN_PROGRESS."
            )
        txn.status = status
        txn.save()
        # tell client that the vendor has accepted the txn, and has started processing it already.
        if status == IN_PROGRESS:
            BusinessAsyncOperations.notify_client_of_txn_status.delay(
                txn_id=txn.id
            )
        return txn
