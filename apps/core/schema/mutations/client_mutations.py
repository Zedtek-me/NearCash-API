import logging
import graphene

from graphql_jwt.decorators import login_required
from django.db.transaction import atomic

from apps.wallet.schema.types.wallet import TransactionType
from apps.wallet.schema.types.wallet import InitiateTransactionInputType

from utils.core_utils.business_utils import BusinessUtil


logger = logging.getLogger("nearcash")
logger.setLevel(logging.DEBUG)

class InitiateTransaction(graphene.Mutation):

    message = graphene.String()
    transaction = graphene.Field(TransactionType)

    class Arguments:
        transaction_data = InitiateTransactionInputType(required=True)

    @login_required
    @atomic
    def mutate(self, info, transaction_data):
        """a client initiates a withdrawal interest transaction."""
        try:
            txn = BusinessUtil.initiate_transaction(info.context.user, transaction_data)
        except Exception as e:
            logger.exception(f"Failed to initiate transaction: {e}")
            raise e
        return InitiateTransaction(
            message="Transaction initiated successfully.",
            transaction=txn
        )

class Mutation(graphene.ObjectType):
    initiate_transaction = InitiateTransaction.Field(
        description="Initiates a transaction for a client."
    )
