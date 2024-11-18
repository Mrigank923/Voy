"""
ASGI config for voy project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/howto/deployment/asgi/
"""

import os
import django
from django.core.asgi import get_asgi_application

from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from rides.middleware import TokenAuthMiddleware  
from voy.routing import websocket_urlpatterns

from rides import consumers 


os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'voy.settings')
django.setup()



application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": TokenAuthMiddleware(
        URLRouter(
            websocket_urlpatterns
        )
    ),
})
