import logging
import traceback
from collections import deque

import orjson
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.contrib.auth.models import AnonymousUser
from django.core.cache import cache
from node_red.models import Element, ElementPermissionsUser

# Setup a logger for this module
logger = logging.getLogger(__name__)

# Define constants for permissions to avoid magic strings
PERM_READ_WRITE = "RC"
PERM_READ_ONLY = "R"


class BrowserConsumer(AsyncWebsocketConsumer):
    """
    Handles WebSocket connections for browser clients.

    This consumer manages user subscriptions to data elements, enforces
    permissions, and facilitates real-time communication between the
    browser and backend systems.
    """

    # --------------------------------------------------------------------------
    # WebSocket Lifecycle Methods
    # --------------------------------------------------------------------------

    async def connect(self):
        """
        Handles a new WebSocket connection from a browser client.
        Authenticates the user and initializes the connection state.
        """
        self.user = self.scope.get("user")
        if not self.user or isinstance(self.user, AnonymousUser):
            await self.close(code=4000)
            return

        # Stores element_id -> permissions mapping
        self.subscriptions = {}
        await self.accept()

    async def disconnect(self, close_code):
        """
        Handles WebSocket disconnection.
        Cleans up by leaving all subscribed channel groups.
        """
        # Create a copy of keys to safely iterate while groups might be modified elsewhere
        subscribed_groups = list(self.subscriptions.keys())
        for group_name in subscribed_groups:
            await self.channel_layer.group_discard(group_name, self.channel_name)
        
        logger.info(f"WebSocket disconnected for user {self.user.username} with code: {close_code}")

    # --------------------------------------------------------------------------
    # Incoming Message Router
    # --------------------------------------------------------------------------

    async def receive(self, text_data):
        """
        Routes incoming messages from the WebSocket to appropriate handlers.
        """
        try:
            data = orjson.loads(text_data)
            message_type = data.get("type")

            if message_type == "subscribe":
                await self._handle_subscribe(data)
            elif message_type == "unsubscribe":
                await self._handle_unsubscribe(data)
            elif message_type == "message_element":
                await self._handle_publish_message(data)
            else:
                await self._send_error_response("unknown_type", f"Unknown message type: {message_type}")

        except (orjson.JSONDecodeError, KeyError) as e:
            logger.warning(f"Invalid message format from user {self.user.username}: {e}")
            await self._send_error_response("invalid_format", str(e), details=text_data)
        except Exception as e:
            logger.error(f"An unexpected error occurred for user {self.user.username}: {e}\n{traceback.format_exc()}")
            await self._send_error_response("server_error", str(e), details=traceback.format_exc())

    # --------------------------------------------------------------------------
    # Group Message Handlers (from Channel Layer)
    # --------------------------------------------------------------------------

    async def forward_element_message(self, event):
        """
        Forwards a message from an element group to the client.
        This consumer will not send messages that originated from itself.
        """
        if event.get('origin_channel') == self.channel_name:
            return
        
        await self.send(text_data=orjson.dumps({
            "type": "message_element",
            "element_id": event["element_id"],
            "message": event["message"]
        }).decode("utf-8"))

    async def permissions_updates(self, event):
        """
        Handles real-time updates to user permissions for an element.
        It re-evaluates permissions and updates or terminates subscriptions.
        """
        element_id = event.get("message", {}).get("element")
        if not element_id or element_id not in self.subscriptions:
            return

        permission, _ = await self.db_get_element_and_permission(self.user, element_id)
        
        if permission:
            # Permission still exists, update it if changed
            if self.subscriptions.get(element_id) != permission.permissions:
                self.subscriptions[element_id] = permission.permissions
                await self.send(text_data=orjson.dumps({
                    "type": "permissions_update",
                    "element_id": element_id,
                    "permissions": permission.permissions
                }).decode("utf-8"))
        else:
            # Permission has been revoked, force unsubscribe
            await self._perform_unsubscribe(element_id)
            await self.send(text_data=orjson.dumps({
                "type": "unsubscribe",
                "element_id": element_id,
                "unsubscribe": True,
                "reason": "Permission revoked"
            }).decode("utf-8"))
            
    async def element_connection_status(self, event):
        """
        Forwards element connection status updates (e.g., from Node-RED) to the client.
        """
        element_id = event.get("element_id")
        if element_id in self.subscriptions:
             await self.send(text_data=orjson.dumps(event).decode("utf-8"))

    # --------------------------------------------------------------------------
    # Internal Helper Methods
    # --------------------------------------------------------------------------

    async def _handle_subscribe(self, data):
        """Handles a subscription request for an element."""
        element_id = data["element_id"]
        permission, element = await self.db_get_element_and_permission(self.user, element_id)

        if not permission or not element:
            await self._send_error_response("permission_denied", "You do not have permission to access this element.", element_id=element_id)
            return
            
        # Join the channel for element data
        await self.channel_layer.group_add(element_id, self.channel_name)
        
        # Join a group specific to this permission object to receive updates
        permission_group_name = f"perm_{permission.id}"
        await self.channel_layer.group_add(permission_group_name, self.channel_name)

        # Store the subscription and permission level
        self.subscriptions[element_id] = permission.permissions
        self.subscriptions[permission_group_name] = "permission_listener" # A marker

        # Confirm subscription to the client
        await self.send(text_data=orjson.dumps({
            "type": "subscribe",
            "element_id": element_id,
            "subscribed": True,
            "permissions": permission.permissions,
            "details": element.details,
            "connected": await element.is_connected()
        }).decode("utf-8"))

        # Send cached points to the new subscriber
        await self._send_cached_points(element_id, element.points)

    async def _handle_unsubscribe(self, data):
        """Handles an unsubscription request."""
        element_id = data["element_id"]
        await self._perform_unsubscribe(element_id)
        await self.send(text_data=orjson.dumps({
            "type": "unsubscribe",
            "element_id": element_id,
            "unsubscribe": True
        }).decode("utf-8"))

    async def _handle_publish_message(self, data):
        """Handles a message sent from the client to be published to an element."""
        element_id = data["element_id"]
        
        # Check if user is subscribed and has write permission
        if self.subscriptions.get(element_id) != PERM_READ_WRITE:
            await self._send_error_response(
                "unauthorized",
                "You do not have permission to send messages to this element.",
                element_id=element_id
            )
            return

        # Broadcast the message to the element's group
        await self.channel_layer.group_send(
            element_id,
            {
                "type": "forward_element_message",
                "element_id": element_id,
                "message": data["message"],
                "origin_channel": self.channel_name,
                "user_id": self.user.id,
                "user": self.user.username
            }
        )

    async def _perform_unsubscribe(self, element_id):
        """Core logic to remove a consumer from an element's groups."""
        if element_id in self.subscriptions:
            await self.channel_layer.group_discard(element_id, self.channel_name)
            self.subscriptions.pop(element_id, None)
            
            # Also remove from any related permission groups (this part needs a robust mapping)
            # For simplicity, we iterate, but a better approach would be a reverse mapping.
            perm_groups_to_remove = [k for k in self.subscriptions if k.startswith("perm_")]
            for group in perm_groups_to_remove:
                 await self.channel_layer.group_discard(group, self.channel_name)
                 self.subscriptions.pop(group, None)

    async def _send_cached_points(self, element_id, max_points):
        """Fetches and sends cached data points for an element to the client."""
        cache_key = f"cache:{element_id}"
        cached_queue = cache.get(cache_key, deque(maxlen=max_points))
        # Send points one by one
        for point in list(cached_queue):
            await self.send(text_data=orjson.dumps({
                "type": "message_element",
                "message": point,
                "element_id": element_id
            }).decode("utf-8"))

    async def _send_error_response(self, error_code, description, **kwargs):
        """Sends a standardized error message to the client."""
        payload = {
            "type": "error",
            "error_code": error_code,
            "description": description,
            **kwargs
        }
        await self.send(text_data=orjson.dumps(payload).decode("utf-8"))

    # --------------------------------------------------------------------------
    # Database Methods
    # --------------------------------------------------------------------------

    @staticmethod
    @database_sync_to_async
    def db_get_element_and_permission(user, element_id):
        """
        Fetches an element and the user's maximum permission for it from the DB.
        Returns a tuple (permission_object, element_object) or (None, None).
        """
        try:
            element = Element.objects.select_related('device').get(id=element_id)
            permission = ElementPermissionsUser.permission_manager.get_max_permission(user, element)
            return permission, element
        except Element.DoesNotExist:
            return None, None