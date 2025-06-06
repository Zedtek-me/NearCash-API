from django.urls import path, include
from rest_framework.routers import DefaultRouter

router = DefaultRouter(trailing_slash=False)


urlpatterns = [
    path("", include(router.urls))
]
