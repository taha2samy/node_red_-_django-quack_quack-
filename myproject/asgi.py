import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter

from channels.middleware import BaseMiddleware
from channels.auth import AuthMiddlewareStack

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'myproject.settings')

django_asgi_app = get_asgi_application()
from node_red.middleware import AuthMiddlewareDevice
from node_red.routing_devices import websocket_urlpatterns
from node_red.routing_browser import websocket_urlpatterns_browser

class MiddlewareDistrubuter:
    def __init__(self, inner_app):
        self.inner_app = inner_app

    async def __call__(self, scope, receive, send):
        if scope["path"].startswith("/device/node_red"):
            inner_app = AuthMiddlewareDevice(self.inner_app)
        elif scope["path"].startswith("/browser/simple/"):
            inner_app = AuthMiddlewareStack(self.inner_app)
        else:
            # Close the connection if the path does not match any of the specified patterns
            await send({
                "type": "websocket.close",
                "code": 4000,
            })
            return
        return await inner_app(scope, receive, send)


websocket_pattern=websocket_urlpatterns+websocket_urlpatterns_browser
application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": MiddlewareDistrubuter(
        URLRouter(websocket_pattern)
    ),
})