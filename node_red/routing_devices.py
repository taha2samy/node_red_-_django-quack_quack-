from django.urls import path
from .consumers.nodered import NodeRedConsumer

websocket_urlpatterns = [
    path('device/node_red/', NodeRedConsumer.as_asgi()),  # Define your WebSocket URL pattern
]


