from django.conf import settings
from interfaces.payment.payment_interface import PaymentInterface

from utils.https.client import Client
from utils.helpers.exception import CustomException
from utils.helpers.general import generate_unique_id
from utils.helpers.logs import logger
from utils.helpers.encryption import decrypt_data_with_fernet

from apps.auths.models import User, UserProfile
from apps.wallet.models import Transaction
from apps.payment.models import PaymentPlatformToken



class PaymentService(PaymentInterface):
    PROVIDERS = {
        "flutterwave": {
            "url": f"{settings.FLUTTERWAVE_BASE_URL}",
            "default_headers": {
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        }
    }

    provider: str | None = None
    client: Client = Client()

    def __init__(self, provider: str = "flutterwave"):
        if provider not in self.PROVIDERS:
            raise CustomException(f"invalid provider given: {provider}")

        url = self.PROVIDERS.get(provider, {}).get("url", "")
        headers = self.PROVIDERS.get(provider, {}).get("default_headers", {})
        token_info = PaymentPlatformToken.fetch_token_info(provider.upper())
        decrypted_access_token = decrypt_data_with_fernet(token_info.token) if token_info and token_info.token else ""
        headers["Authorization"] = f"Bearer {decrypted_access_token}"
        self.__class__.provider = provider
        self.__class__.client = Client(
            base_url=url,
            headers=headers
        )

    @classmethod
    def get_virtual_account(
        cls, client: User, trxn: Transaction, *args, **kwargs
    ) -> dict:
        """
        fetches virtual account from an escrow provider
        """
        response = {}
        if cls.provider == "flutterwave":
            response = cls.get_flutterwave_virtual_account(
                client, trxn, *args, **kwargs
            )
        return response


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


    @classmethod
    def get_flutterwave_virtual_account(
        cls, client: User, trxn: Transaction,
        *args, **kwargs
    ) -> dict:
        """
        gets virtual account from paystack
        """
        client_customer_info = cls._create_client_as_account_customer(client)
        if not client_customer_info or client_customer_info.get("id") is None:
            logger.error(f"couldn't retrieve client customer info.\n got response: {client_customer_info}")
            return {}

        idempotency_key = generate_unique_id()
        trace_id = generate_unique_id(30)
        endpoint = "/virtual-accounts"
        headers = {
            "X-Idempotency-Key": idempotency_key,
            "X-Trace-Id": trace_id,
            "X-Scenario-Key": "issuer:approved"
        }
        reference = kwargs.get("reference") or trxn.txn_ref
        payload = {
            "customer_id": client_customer_info.get("id"),
            "reference": reference,
            "expiry": settings.FLUTTERWAVE_DYNAMIC_VIRTUAL_ACCOUNT_EXPIRY,
            "amount": trxn.amount,
            "currency": trxn.currency,
            "account_type": "dynamic",
            "narration": f"{client.full_name} to lock request with vendor."
        }
        if client.profile.nin:
            payload.update({"nin": client.profile.nin})
        else:
            payload.update({"bvn": client.profile.bvn})
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
            "info": account_data,
            "txn_idempotency_key": idempotency_key,
            "txn_trace_id": trace_id,
            "transfer_status": "pending"
        }
        trxn.save()
        return response
