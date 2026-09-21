import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'my_shop.settings')
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

from apps.accounts.routing import websocket_urlpatterns as accounts_ws
from admin_panel.routing import websocket_urlpatterns as admin_ws

django_asgi_app = get_asgi_application()
websocket_urlpatterns = accounts_ws + admin_ws

application = ProtocolTypeRouter({
    'http': django_asgi_app,
    # Без AllowedHostsOriginValidator — пропускает WebSocket с любого Origin
    'websocket': AuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})