from rest_framework.routers import DefaultRouter

from .views import PaymentHookViewSet

router = DefaultRouter(trailing_slash=False)
router.register(
    "payment/hooks", PaymentHookViewSet, basename="payment"
)

urlpatterns = []

urlpatterns += router.urls
