import graphene
from graphql_jwt.decorators import login_required

from apps.payment.schema.types.payment_types import BankAccountInfoType
from apps.payment.services import PaymentService

from utils.wallet_utils.transactions import TransactionUtil
from utils.helpers.exception import CustomException
from utils.helpers.general import generate_unique_id

class GenerateVirtualAccount(graphene.Mutation):
    message = graphene.String()
    account_info = graphene.Field(BankAccountInfoType)

    class Arguments:
        txn_id = graphene.String(required=True)


    @login_required
    def mutate(self, info, **kwargs):
        client_user = info.context.user
        trxn_id = kwargs.get("txn_id")
        trxn = TransactionUtil.get_transaction(id=trxn_id)
        if not trxn:
            raise CustomException(
                message=f"Invalid transaction id: {trxn_id}!"
            )
        current_virtual_account_info = trxn.meta.get("virtual_account", {})
        provider = current_virtual_account_info.get("provider", "flutterwave")
        p_s = PaymentService(provider)
        response = p_s.get_virtual_account(client_user, trxn, reference=f"{trxn.txn_ref}-regen-{generate_unique_id(5)}")
        data: dict = response.get("data", {})
        data.pop("customer_id", None)
        data.pop("id", None)
        data.update({"provider": provider, "account_name": client_user.full_name})
        return GenerateVirtualAccount(
            message="Account successfully generated!",
            account_info=data
        )


class Mutation(graphene.ObjectType):
    generate_virtual_account = GenerateVirtualAccount.Field(
        description="Used to generate a fresh virtual account from a provider"
    )
