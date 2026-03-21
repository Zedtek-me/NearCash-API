from django.conf import settings
from interfaces.payment.payment_interface import PaymentInterface

from utils.https.client import Client
from utils.helpers.exception import CustomException
from utils.helpers.general import generate_unique_id
from utils.helpers.logs import logger

from apps.auths.models import User, UserProfile
from apps.wallet.models import Transaction


class PaymentService(PaymentInterface):
    PROVIDERS = {
        "flutterwave": {
            "url": f"{settings.FLUTTERWAVE_BASE_URL}",
            "default_headers": {
                "Accept": "application/json",
                "Content-Type": "application/json",
                "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}"
            }
        }
    }

    provider: str | None = None
    client: Client = Client()

    def __init__(self, provider: str = "flutterwave"):
        if provider not in self.PROVIDERS:
            raise CustomException(f"invalid provider given: {provider}")
        self.__class__.provider = provider
        self.__class__.client = Client(
            base_url=self.PROVIDERS.get(provider, {}).get("url", ""),
            headers=self.PROVIDERS.get(provider, {}).get("default_headers", {})
        )

    @classmethod
    def get_virtual_account(
        cls, client: User, trxn: Transaction, *args, **kwargs
    ) -> dict:
        """
        fetches virtual account from an escrow provider
        """
        client_customer_info = cls._create_client_as_account_customer(client)
        logger.debug(f"client customer info retrieved:::: {client_customer_info}")

        endpoint = "/virtual-accounts"
        headers = {
            "X-Idempotency-Key": generate_unique_id(),
            "X-Trace-Id": generate_unique_id(30)
        }
        payload = {
            "customer_id": client_customer_info.get("id"),
            "reference": trxn.txn_ref,
            "expiry": 60,
            "amount": trxn.amount,
            "currency": trxn.currency,
            "account_type": "dynamic",
            "narration": "Cash Request Locking",
            "nin": client.profile.nin
        }
        response = cls.client.post(
            endpoint=endpoint,
            headers=headers,
            payload=payload
        )
        logger.debug(f"virtual account creation response:::: {response}")
        if not response or response.get("status") != "success":
            # TODO: rather than raising an exception here,
            # we want to publish to both the client and vendor
            # that the system is unable to generate virtual account now
            # Part of the messaget to the client will involve asking if they want
            # to switch to card form of transfer, while message to the vendor will
            # include something like: confirming if client would like to switch to card
            # if client responds with "switch_to_card", then we notify the vendor to proceed
            # in fulfilling the transaction. Otherwise, we cancel the transaction, and notify the vendor
            # NOTE: requesting client's decision will come with expiry. If client doesn't respond within
            # the given time-frame, the transaction is cancelled.
            raise CustomException(
                message="Unable to create virtual account at the moment!"
            )
        account_data = response.get("data", {})
        trxn.meta["virtual_account"] = {
            "provider": cls.provider,
            "info": account_data
        }
        trxn.save()
        return account_data


    @classmethod
    def initiate_payout(
        cls, *args, **kwargs
    ) -> dict:
        """
        payout to the vendor's bank accounts
        """
        return {}


    @classmethod
    def _create_client_as_account_customer(
        cls, client: User
    ) -> dict:
        """
        creates the client on the virtual account provider as a client
        if the user doesn't exist yet on the platform
        """
        from utils.user_utils.users import UserUtil

        provider = cls.provider or "flutterwave"
        existing_customer_info = UserUtil.fetch_user_thirdparty_customer_info(client, provider)
        if existing_customer_info:
            return existing_customer_info
        payload = {
            "name": {
                "first": client.first_name,
                "last": client.last_name
            },
            "email": client.email
        }
        headers = {
            "X-Idempotency-Key": generate_unique_id()
        }
        if cls.provider == "paystack":
            # update payload and headers according to paystack required info
            payload = {}
            headers = {}
        response = cls.client.post(
            "/customers", headers, payload=payload
        )
        logger.debug(f"response from customer creation::: {response}")
        if not response or response.get("status") != "success":
            return {}
        profile: UserProfile = client.profile
        profile.thirdparty_payment_customer_info[provider] = response.get("data", {})
        profile.save()
        return response.get("data", {})
