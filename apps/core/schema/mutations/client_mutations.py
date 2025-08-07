import logging
import graphene

from graphql_jwt.decorators import login_required

from apps.wallet.schema.types.wallet import TransactionType
from apps.wallet.schema.types.wallet import InitiateTransactionInputType

from utils.core_utils.business_utils import BusinessUtil


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

class InitiateTransaction(graphene.Mutation):

    message = graphene.String()
    transaction = graphene.Field(TransactionType)

    class Arguments:
        transaction_data = InitiateTransactionInputType(required=True)

    @login_required
    def mutate(self, info, transaction_data):
        """a client initiates a withdrawal interest transaction."""
        txn = BusinessUtil.initiate_transaction(info.context.user, transaction_data)
        logger.debug(f"Transaction initiated: {txn.id} for user: {info.context.user.id}")
        return InitiateTransaction(
            message="Transaction initiated successfully.",
            transaction=txn
        )

class Mutation(graphene.ObjectType):
    initiate_transaction = InitiateTransaction.Field(
        description="Initiates a transaction for a client."
    )
