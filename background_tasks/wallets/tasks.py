from celery import shared_task

from utils.helpers.logs import logger

class WalletAsyncOperations:

    @shared_task(
        bind=True, name="optionally-create-user-wallet"
    )
    def optionally_create_user_wallet(
        self, user_type: str, user_id: str
    ):
        """
        checks to confirm that user doesn't current have a wallet
        before deciding to create one for the user
        """
        from utils.auth_utils.auths import AuthUtils
        from utils.wallet_utils.wallet import WalletUtil

        user = AuthUtils.fetch_user({"id": user_id, "meta__user_type": user_type.upper()})

        wallet = WalletUtil.get_wallet({"user_id": user.id}, False)
        if not wallet:
            wallet_data = {
                "user_id": user.id,
                "currency": "NGN"
            }
            wallet = WalletUtil.create_wallet(wallet_data)
        return wallet
