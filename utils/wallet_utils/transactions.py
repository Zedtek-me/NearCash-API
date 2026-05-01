import uuid

from django.db.models import Q

from apps.wallet.models import Transaction
from apps.auths.models import User
from apps.notification.email.app_emails import EmailService

from utils.helpers.exception import CustomException
from utils.helpers.logs import logger
from utils.helpers.general import generate_random_codes

from apps.wallet.constants import (
    IN_PROGRESS, CANCELLED,
    FULFILLED, TXN_STATUSES
)

from celery import shared_task
from near_cash.celery import BaseTask

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
        from background_tasks.core.tasks import BusinessAsyncOperations
        from utils.notifications.notifications import NotificationUtil

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
        # if client is the one who cancelled, notify vendor
        if status == CANCELLED and user.id == txn.client.id:
            BusinessAsyncOperations.notify_vendor_about_transaction.delay(txn_id=txn.id)
            return

        BusinessAsyncOperations.notify_client_of_txn_status.delay(
            txn_id=txn.id
        )
        return txn

    @shared_task(bind=True, name="update_inprogress_transactions", base=BaseTask)
    def update_inprogress_transactions(self: BaseTask):
        """
        checks for transactions that have been in the IN_PROGRESS
        for too long after the initiation date and time; if found,
        marks send a reminder to both the client and the vendor to
        update the txn status appropriately -- whether successful or canceled
        """
        ...


    @classmethod
    def update_trxn_info_with_account_details(
        cls, trxn: Transaction, trxn_info: dict, client: User
    ) -> dict:
        """
        updates the given transaction info
        with a virtual account detail generated via account provider (flutter or paystack)
        """
        from apps.payment.services import PaymentService

        # flutterwave first
        p_s = PaymentService(provider="flutterwave")
        account_response = p_s.get_virtual_account(client=client, trxn=trxn)
        if not account_response or account_response.get("status") != "success":
            p_s.__class__.provider = "paystack"
            account_response = p_s.get_virtual_account(client=client, trxn=trxn)
        # then try paystack if needed
        if not account_response or account_response.get("status") != "success":
            logger.error("unable to generate virtual account!!!")
            account_response =  {}
        account_data = account_response.get("data") or {}
        account_data.pop("id", None)
        account_data.pop("customer_id", None)
        account_data.update({
            "provider": p_s.provider,
            "account_name": client.full_name
        })
        trxn_info.update({
            "account_info": account_data
        })
        return trxn_info


    @classmethod
    def populate_trxn_info_with_default_account_detail(
        cls, trxn_info: dict
    ) -> dict:
        from utils.helpers.general import get_two_formatted_datetime

        default_created_time, default_expiry = get_two_formatted_datetime(5)
        trxn_info.update({
            "account_info": {
                "note": "Unable to generate virtual account at the moment. Try again in 5 seconds",
                "amount": 0.0, "status": "unavailable",
                "currency": "NGN", "reference": "Unavailable",
                "created_datetime": default_created_time,
                "account_bank_name": "Unavailable",
                "account_expiration_datetime": default_expiry
            }
        })
        return trxn_info


    @classmethod
    def generate_and_send_confirmation_code(
        cls, trxn: Transaction, for_vendor: bool = False
    ) -> None:
        """
        generates and send confirmation code to the
        appropriate user
        """
        code = generate_random_codes()
        client: User = trxn.client
        vendor: User = trxn.vendor
        user_type = "client" if not for_vendor else "vendor"
        recipients = [ client.email if not for_vendor else vendor.email ]
        context = {
            "confirmation_code": code,
            "user_type": user_type,
            "user_fullname": client.full_name if not for_vendor else vendor.full_name
        }
        EmailService.send_mail_async.delay(**{
            "subject": "Transaction Confirmation Code",
            "body": "confirmation_code.html",
            "recipients": recipients,
            "context": context
        })
        # TODO: also send confirmation code via sms
