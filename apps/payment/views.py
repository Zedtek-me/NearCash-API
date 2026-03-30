from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request

from django.views.decorators.csrf import csrf_exempt

from utils.helpers.logs import logger
from utils.https.parsers import HttpPerser

from near_cash.middlewares.rest_auth_permissions import HookSignatureValid

from apps.payment.services import PaymentService

from background_tasks.payments.tasks import PaymentAsyncOperations


class PaymentHookViewSet(ViewSet):

    def get_permissions(self):
        request = self.request
        action_map: dict = self.action_map
        method: str = (request.method and request.method.lower()) or ""
        endpoint_called: str = action_map.get(method, "")
        if endpoint_called == "handle_flutterwave_hook":
            return [ HookSignatureValid() ]
        return [ AllowAny() ]

    @csrf_exempt
    @action(detail=False, methods=["post"], url_path="flutterwave")
    def handle_flutterwave_hook(self, request: Request):
        logger.debug(f"initial data from flutterwave event:::: {request.data}")
        data: dict = request.data
        PaymentService.process_flutterwave_event(data)
        return HttpPerser.success(data={"message": "event successfully received!"})
