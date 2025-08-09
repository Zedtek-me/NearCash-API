"""
ASGI config for near_cash project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application

from channels.routing import URLRouter, ProtocolTypeRouter
from channels.auth import AuthMiddlewareStack
from apps.notification.websockets.routers import ws_urlpatterns

from .middlewares.custom_socker_middleware import CustomSocketAuthMiddleware

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'near_cash.settings')

application = get_asgi_application()

application = ProtocolTypeRouter({
    "http": application,
    "websocket": 
        CustomSocketAuthMiddleware(
         URLRouter(ws_urlpatterns)   
        ),
})