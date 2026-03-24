from rest_framework.viewsets import ViewSet
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.request import Request

from apps.payment.serializers import FlutterWaveHookSerializer

from utils.helpers.logs import logger
from utils.https.parsers import HttpPerser


class PaymentHookViewSet(ViewSet):

    @action(detail=False, methods=["post"], url_path="flutterwave")
    def handle_flutterwave_hook(self, request: Request):
        serializer = FlutterWaveHookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        logger.debug(f"webhook data from flutterwave::::: {data}")
        return HttpPerser.success(data={"message": "event successfully received!"})
