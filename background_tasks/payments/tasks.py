from celery import shared_task

from django.db.models import Q
from django.db import transaction

from utils.helpers.logs import logger
from utils.helpers.exception import CustomException

from apps.wallet.models import Transaction



class PaymentAsyncOperations:
    @shared_task(bind=True, name="process-payment-event")
    def process_event(
        self, source: str, event: dict
    ) -> bool:
        """
        persists event in the db;
        then handle all other operations around the event processing
        """
        event_type = event.get("type")
        with transaction.atomic():
            match event_type:
                case "charge.completed":
                    PaymentAsyncOperations._process_charge_event(source, event)
                case _:
                    logger.error(f"No handler for event: `{event_type}` yet!")
            transaction.on_commit(
                lambda: True
            )

    @staticmethod
    def _process_charge_event(
        source: str,
        event_data: dict
    ) -> bool:
        """
        charge event processing
        """
        from apps.payment.models import PaymentPlatformEvent
        from utils.wallet_utils.transactions import TransactionUtil

        logger.debug(f"event data passed into webhook:::: {event_data}")
        db_event = PaymentPlatformEvent(
            source=source, event=event_data
        )
        charge_data: dict = event_data.get("data", {})
        payment_method: dict = charge_data.get("payment_method", {})
        trxn_ref = charge_data.get("reference", "")
        amount: float = charge_data.get("amount", 0.0)
        currency: str = charge_data.get("currency", "")
        status: str = charge_data.get("status", "")
        search_filter = Q()
        if source.lower() == "flutterwave":
            search_filter = (
                Q(txn_ref__iexact=trxn_ref) | Q(
                    meta__has_key="virtual_account", meta__virtual_account__has_key="flutter_reference",
                    meta__virtual_account__flutter_reference=trxn_ref
                )
            )
        trxn = TransactionUtil.get_transaction(search_filter=search_filter)
        logger.debug(f"trxn_ref from event data:: {trxn_ref}\nsearch filter used for trxn lookup:: {search_filter}\ntransaction found for event::::: {trxn}")
        if not trxn:
            raise CustomException(
                message="couldn't find a transaction for this event!"
            )
        db_event.transaction = trxn
        db_event.save()

        successfully_processed = False
        if payment_method.get("type", "").lower() == "bank_transfer":
            payment_method.update({
                "amount": amount,
                "currency": currency,
                "status": status
            })
            successfully_processed = PaymentAsyncOperations._process_bank_transfer_charge(
                source, trxn, payment_method
            )

        if not successfully_processed:
            # publish to both vendor and client on unsuccessful payment
            PaymentAsyncOperations._notify_client_on_transfer_status(trxn=trxn)
            PaymentAsyncOperations._notify_vendor_on_transfer_status(trxn=trxn)
            return False
        # for a successful transfer, notify both vendor and client again
        PaymentAsyncOperations._notify_client_on_transfer_status(
            trxn, status_msg_type="Transfer Confirmed"
        )
        PaymentAsyncOperations._notify_vendor_on_transfer_status(
            trxn, status_msg_type="Transfer Confirmed"
        )
        # TODO: generate a code for the client when transaction is confirmed successful.
        return True


    @staticmethod
    def _process_bank_transfer_charge(
        source: str,
        trxn: Transaction | None,
        payment_method_data: dict
    ) -> bool:
        status: str = payment_method_data.get("status", "")
        currency: str = payment_method_data.get("currency", "")
        amount: float = payment_method_data.get("amount", 0.0)
        if not trxn:
            raise CustomException(
                message="transaction not found for this event!!!"
            )
        trxn_curr = trxn.currency
        trxn_amount = trxn.amount
        source = (source or "").lower()
        # update according to payment provider
        match source:
            case "flutterwave":
                if status != "succeeded" or currency != trxn_curr or amount != trxn_amount:
                    logger.exception(
                        "Declining transaction due to one or two mismatch "
                        f"in event payment data::: {payment_method_data}"
                    )
                    trxn.status = "DECLINED"
                    trxn.meta["decline_reason"] = (
                        "currency mismatch" if currency != trxn_curr else (
                            "amount mismatch" if amount != trxn_amount else "charge failed from sender's bank!"
                        )
                    )
                    trxn.save()
                    return False
                # if all conditions pass, update transfer status
                virtual_account_info = trxn.meta["virtual_account"] or {}
                virtual_account_info.update(transfer_status="success")
                trxn.meta["virtual_account"] = virtual_account_info
                trxn.save()
            case _:
                logger.debug(f"unable to handle transaction source:: {source} :: for now.")
        return True


    @staticmethod
    def _get_vendor_and_client_msg_customs(
        custom_msg_type: str, trxn: Transaction,
        for_client: bool = True
    ) -> tuple[str | None, str | None, str | None]:
        if custom_msg_type == "Transfer Failed" and for_client:
            reason = trxn.meta.get("decline_reason", "cannot process transfer!")
            custom_body = f"We could not verify your transfer due to {reason}. Your Transaction Has been declined!"
            return (
                custom_msg_type, custom_msg_type, custom_body
            )

        # for vendor
        if custom_msg_type == "Transfer Failed":
            reason = trxn.meta.get("decline_reason", "cannot process transfer!")
            custom_body = f"client transfer was declined due to {reason}"
            return (
                custom_msg_type, custom_msg_type, custom_body
            )

        if custom_msg_type == "Transfer Confirmed" and for_client:
            confirmation_provider = trxn.meta.get("virtual_account", {})\
                .get("provider", "flutterwave")
            confirmed_amount = trxn.amount
            custom_body = f"Your Transfer of {confirmed_amount} has been confirmed by NearCash on {confirmation_provider}!"
            return (
                custom_msg_type, custom_msg_type, custom_body
            )
        if custom_msg_type == "Transfer Confirmed":
            # for vendor
            confirmed_amount = trxn.amount
            trxn_ref = trxn.txn_ref
            trxn_currency = trxn.currency
            custom_body = f"Transfer of {confirmed_amount}{trxn_currency} for transaction {trxn_ref} has been confirmed by NearCash.\n Please Proceed with the transaction."
            return (
                custom_msg_type, custom_msg_type, custom_body
            )
        return (None, None, None)


    @staticmethod
    def _notify_client_on_transfer_status(
        trxn: Transaction,
        status_msg_type: str = "Transfer Failed"
    ):
        from utils.notifications.notifications import NotificationUtil

        [
            title, msg_type,
            msg_body
        ] = PaymentAsyncOperations._get_vendor_and_client_msg_customs(
                status_msg_type, trxn
            )

        NotificationUtil.send_socket_notification(
            trxn, for_vendor_notif=False,
            custom_body=msg_body,
            custom_title=title,
            custom_msg_type=msg_type
        )


    @staticmethod
    def _notify_vendor_on_transfer_status(
        trxn: Transaction,
        status_msg_type: str = "Transfer Failed"
    ):
        from utils.notifications.notifications import NotificationUtil

        [
            title, msg_type,
            msg_body
        ] = PaymentAsyncOperations._get_vendor_and_client_msg_customs(
                status_msg_type, trxn, for_client=False
            )

        NotificationUtil.send_socket_notification(
            trxn, custom_body=msg_body,
            custom_title=title,
            custom_msg_type=msg_type
        )
