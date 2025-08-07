from django.urls import re_path

from apps.notification.websockets.consumers import NotificationConsumer



ws_urlpatterns = [
    re_path(r'ws/notification/(?P<user_id>\w+)/$', NotificationConsumer.as_asgi()),
]
