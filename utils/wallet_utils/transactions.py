import uuid

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
        cls, only_one: bool = True, **_filter
    ) -> Transaction:
        txns = Transaction.objects.filter(**_filter).select_related(
            "client", "vendor", "asset", "business"
        )
        if only_one:
            return txns.first()
        return txns
