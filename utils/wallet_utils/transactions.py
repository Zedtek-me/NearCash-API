import uuid

from django.db.models import Q

from apps.wallet.models import Transaction

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
