import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_shop.settings')

# Инициализируем Django ДО импорта routing/consumers
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from channels.security.websocket import AllowedHostsOriginValidator

# Импортируем routing ПОСЛЕ django.setup()
from apps.accounts.routing import websocket_urlpatterns as accounts_ws
from admin_panel.routing import websocket_urlpatterns as admin_ws

django_asgi_app = get_asgi_application()

websocket_urlpatterns = accounts_ws + admin_ws

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        AuthMiddlewareStack(
            URLRouter(websocket_urlpatterns)
        )
    ),
})