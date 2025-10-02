# ./admin.py
from django.contrib import admin
from .models import Device, Element, ElementPermissionsUser, ElementPermissionsGroup,Connections,JWTPublicKey
import jwt
from datetime import datetime, timedelta
from django.utils.html import format_html


class DeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'public_key', 'description')



admin.site.register(Device, DeviceAdmin)

# Register Connections model to the admin panel
class ConnectionsAdmin(admin.ModelAdmin):
    list_display = ('id','device')
    pass
admin.site.register(Connections, ConnectionsAdmin)
# Register Element model to the admin panel
class ElementAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'element_id', 'points', 'description')
    search_fields = ('name', 'element_id')
    list_filter = ('points',)

admin.site.register(Element, ElementAdmin)

# Register ElementPermissionsUser model to the admin panel
class ElementPermissionsUserAdmin(admin.ModelAdmin):
    list_display = ('user', 'element', 'permissions')
    search_fields = ('user__username', 'element__name')
    list_filter = ('permissions',)

admin.site.register(ElementPermissionsUser, ElementPermissionsUserAdmin)

# Register ElementPermissionsGroup model to the admin panel
class ElementPermissionsGroupAdmin(admin.ModelAdmin):
    list_display = ('group', 'element', 'permissions')
    search_fields = ('group__name', 'element__name')
    list_filter = ('permissions',)

admin.site.register(ElementPermissionsGroup, ElementPermissionsGroupAdmin)

@admin.register(JWTPublicKey)
class JWTPublicKeyAdmin(admin.ModelAdmin):
    list_display = (
        'name', 
        'algorithm', 
        'key_size', 
        'is_active', 
        'created_at'
    )
    
    list_filter = (
        'is_active', 
        'algorithm', 
        'created_at'
    )
    
    search_fields = (
        'name', 
        'public_key'
    )
    
    readonly_fields = (
        'algorithm', 
        'key_size', 
        'created_at'
    )
    
    fieldsets = (
        ('Key Information', {
            'fields': (
                'name', 
                'public_key'
            )
        }),
        ('Detected Properties', {
            'classes': ('collapse',),
            'fields': (
                'algorithm', 
                'key_size'
            )
        }),
        ('Status & Metadata', {
            'fields': (
                'is_active', 
                'created_at'
            )
        }),
    )


# ./all_python_combined.py


# ./apps.py
from django.apps import AppConfig

class NodeRedConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'node_red'
    def ready(self):
        import node_red.signals

# ./consumers/browser.py
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

# ./consumers/___init__.py


# ./consumers/nodered.py
import asyncio
import logging
import socket
import uuid
from collections import deque

import orjson
import psutil
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from django.core.cache import cache
from node_red.models import Connections

# Setup a logger for this module
logger = logging.getLogger(__name__)


class NodeRedConsumer(AsyncWebsocketConsumer):
    """
    A robust WebSocket consumer for real-time data flows.

    This consumer manages device and element-specific channels, handles
    state synchronization, logs connection details securely, and processes
    messages efficiently with proper error handling.
    """

    # --------------------------------------------------------------------------
    # WebSocket Lifecycle Methods
    # --------------------------------------------------------------------------

    async def connect(self):
        """
        Handles a new WebSocket connection.
        Initializes state, joins channel groups, and creates a connection record.
        """
        self._initialize_state()
        await self._join_groups()
        await self.accept()
        self.connection_id = await self._create_connection_record()

    async def disconnect(self, close_code):
        """
        Handles a WebSocket disconnection.
        Leaves all channel groups and removes the connection record.
        """
        await self._leave_groups()
        await self._remove_connection_record(self.connection_id)

    # --------------------------------------------------------------------------
    # Message Handlers
    # --------------------------------------------------------------------------

    async def receive(self, text_data):
        """
        Receives a message from the WebSocket, processes it, updates the cache,
        and broadcasts it to the relevant element group.
        """
        try:
            payload = orjson.loads(text_data)
            element_id = payload['element_id']
            message = payload['message']

            if element_id in self.elements_ids:
                self._update_element_cache(element_id, message)
                
                await self.channel_layer.group_send(
                    element_id,
                    {
                        'type': 'forward_element_message',
                        'element_id': element_id,
                        'message': message,
                        'origin_channel': self.channel_name,
                    }
                )
        except (orjson.JSONDecodeError, KeyError) as e:
            # Log the error instead of silently passing
            logger.warning(
                f"Invalid message format from {self.channel_name}. Error: {e}. Data: {text_data}"
            )

    async def forward_element_message(self, event):
        """
        Forwards a message from a group to the client, but only if the message
        did not originate from this same client.
        """
        if event['origin_channel'] != self.channel_name:
            await self.send(
                text_data=orjson.dumps({
                    'element_id': event['element_id'],
                    'message': event['message'],
                }).decode('utf-8')
            )

    # --------------------------------------------------------------------------
    # Real-time State Synchronization Handlers
    # --------------------------------------------------------------------------

    async def device_updates(self, event):
        """
        Handles real-time updates for the connected device.
        """
        state = event.get('state')
        if state == "update":
            self.device = event.get("message", self.device)
        elif state == "delete":
            await self.close(code=4000)

    async def elements_updates(self, event):
        """
        Handles real-time CRUD updates for the device's elements.
        """
        state = event.get('state')
        element = event.get('message', {})
        element_id = element.get('id')

        if not element_id:
            return

        if state == "create":
            await self.channel_layer.group_add(element_id, self.channel_name)
            self.elements_ids.add(element_id)
            self.elements_data[element_id] = element
        elif state == "update":
            self.elements_data[element_id] = element
        elif state == "delete":
            await self.channel_layer.group_discard(element_id, self.channel_name)
            self.elements_ids.discard(element_id)
            # Use .pop() for safe deletion to avoid KeyError
            self.elements_data.pop(element_id, None)
            
    async def close_connection(self, event):
        """
        Handler to programmatically close the connection if requested.
        """
        if event.get('connection_id') == self.connection_id:
            await self._remove_connection_record(self.connection_id)
            await self.close()
    async def element_connection_status(self, event):
        """
        This consumer is the source of connection truth, so it doesn't need
        to act on these broadcast messages. This handler exists to
        prevent a "No handler" error when messages are sent to a group
        it's subscribed to (alongside BrowserConsumers).
        """
        if event.get('status')=="disconnected":
            logger.info(f"Received element_connection_status event: {event}")
            await self.close()
        pass
    # --------------------------------------------------------------------------
    # Helper & Internal Methods
    # --------------------------------------------------------------------------

    def _initialize_state(self):
        """Initializes consumer state from the connection scope."""
        self.device = self.scope.get('device')
        elements = self.scope.get('element', [])
        self.elements_data = {e['id']: e for e in elements} if elements else {}
        self.elements_ids = set(self.elements_data.keys())
        self.connection_id = None

    async def _join_groups(self):
        """Adds the consumer's channel to all relevant groups."""
        groups_to_join = list(self.elements_ids) + [self.device['id']]
        await asyncio.gather(
            *(self.channel_layer.group_add(group, self.channel_name) for group in groups_to_join)
        )

    async def _leave_groups(self):
        """Removes the consumer's channel from all its groups."""
        groups_to_leave = list(self.elements_ids) + [self.device['id']]
        await asyncio.gather(
            *(self.channel_layer.group_discard(group, self.channel_name) for group in groups_to_leave)
        )

    def _update_element_cache(self, element_id, message):
        """Updates the cache for a given element with a new message."""
        element_data = self.elements_data.get(element_id, {})
        cache_key = f"cache:{element_id}"
        # Provide a default maxlen for the deque
        max_points = element_data.get('points', 100)
        queue = cache.get(cache_key, deque(maxlen=max_points))
        queue.append(message)
        cache.set(cache_key, queue, timeout=None)

    # --------------------------------------------------------------------------
    # Database Interaction Methods
    # --------------------------------------------------------------------------

    async def _create_connection_record(self):
        """
        Securely gathers specific connection details and creates a record
        in the database. Avoids storing the entire scope object.
        """
        # Selectively pick only the required, non-sensitive information
        headers = {key.decode('utf-8', 'ignore'): value.decode('utf-8', 'ignore')
                   for key, value in self.scope.get('headers', [])}

        connection_details = {
            'client': self.scope.get('client'),
            'path': self.scope.get('path'),
            'user_agent': headers.get('user-agent'),
            'server_network': await self._get_server_network_info(),
        }
        return await self.db_create_connection(self.device['id'], connection_details)

    @staticmethod
    @database_sync_to_async
    def db_create_connection(device_id, details):
        """Creates a new connection record in the database."""
        connection = Connections.objects.create(device_id=device_id, details=details)
        return connection.id
        
    async def _remove_connection_record(self, connection_id):
        """Removes the connection record from the database."""
        if connection_id:
            await self.db_remove_connection(connection_id)

    @staticmethod
    @database_sync_to_async
    def db_remove_connection(connection_id):
        """Deletes a connection record by its ID."""
        Connections.objects.filter(id=connection_id).delete()

    # --------------------------------------------------------------------------
    # Static Utility Methods
    # --------------------------------------------------------------------------

    @staticmethod
    async def _get_server_network_info():
        """
        Asynchronously gathers network information about the server host
        without blocking the event loop.
        """
        loop = asyncio.get_running_loop()
        
        # Run synchronous I/O operations in a thread pool executor
        try:
            hostname = await loop.run_in_executor(None, socket.gethostname)
            ip_address = await loop.run_in_executor(None, socket.gethostbyname, hostname)
        except socket.gaierror:
            hostname = "localhost"
            ip_address = "127.0.0.1"
        
        interfaces = []
        try:
            # psutil calls are generally fast and non-blocking, but can be run
            # in an executor for extreme caution if needed.
            if_addrs = psutil.net_if_addrs()
            if_stats = psutil.net_if_stats()
            for name, addrs in if_addrs.items():
                stats = if_stats.get(name)
                if stats and stats.isup:
                    interfaces.append({
                        'interface': name,
                        'mtu': stats.mtu,
                        'is_up': stats.isup,
                        'addresses': [addr.address for addr in addrs if addr.family == socket.AF_INET]
                    })
        except Exception as e:
            logger.error(f"Could not retrieve network interface info: {e}")

        return {
            'host': {
                'hostname': hostname,
                'ip_address': ip_address,
                'interfaces': interfaces
            }
        }

# ./middleware.py
import jwt
import logging
import uuid
from channels.auth import BaseMiddleware
from channels.db import database_sync_to_async
from django.contrib.auth.models import AnonymousUser
from django.db.models import QuerySet
from django.forms.models import model_to_dict
from .models import Device, Element
from channels.exceptions import DenyConnection


logger = logging.getLogger(__name__)

def model_to_dict_updates(instance_or_queryset):
    """
    Helper function to convert model instances or querysets into dictionaries,
    ensuring UUIDs are converted to strings.
    """
    if isinstance(instance_or_queryset, QuerySet):
        return [model_to_dict_updates(instance) for instance in instance_or_queryset]
    
    data = model_to_dict(instance_or_queryset)
    data['id'] = instance_or_queryset.id

    for field, value in data.items():
        if isinstance(value, uuid.UUID):
            data[field] = str(value)
    
    return data

class AuthMiddlewareDevice(BaseMiddleware):
    """
    Middleware that authenticates a device by its ID from the JWT payload.
    It fetches the device's assigned public key from the database to verify the token.
    Connections without a token are treated as anonymous.
    """

    async def __call__(self, scope, receive, send):
        scope['device'] = None
        scope['element'] = []
        scope['user'] = AnonymousUser()

        try:
            auth_header = next(value for key, value in scope["headers"] if key == b"authorization")
            token = auth_header.decode().split(" ")[1]
            
            authenticated_scope = await self.authenticate_and_prepare_scope(token, scope)
            if authenticated_scope:
                scope = authenticated_scope
            else:
                await send({
                    "type": "websocket.close",
                    "code": 4000,  
                    "reason": "Device authentication failed"
                })
                return
                

        except (StopIteration, IndexError):
            await send({
                "type": "websocket.close",
                "code": 4000,
                "reason": "Device authentication failed"
            })
            return
            
        return await super().__call__(scope, receive, send)

    @database_sync_to_async
    def get_device_with_key(self, device_id):
        """
        Fetches the device and its related public key from the database.
        Returns None if the device doesn't exist or has no key assigned.
        """
        try:
            device = Device.objects.select_related('public_key').get(id=device_id)

            if not device.public_key:
                logger.error(f"Device '{device_id}' exists but has no public key assigned.")
                return None
            
            return device
        except Device.DoesNotExist:
            logger.error(f"Device with id='{device_id}' from JWT payload not found in database.")
            return None

    async def authenticate_and_prepare_scope(self, token, scope):
        """
        Authentication logic based on the device_id from the JWT payload.
        """
        device_id = None
        try:
            # 1. Decode the token without signature verification to get the payload.
            unverified_payload = jwt.decode(token, options={"verify_signature": False})
            device_id = unverified_payload.get('id')
            if not device_id:
                 logger.error("JWT payload is missing 'id'.")
                 return None

            # 2. Fetch the device from the database and ensure it has a key assigned.
            device = await self.get_device_with_key(device_id)
            if not device:
                # This handles both non-existent devices and devices without a key.
                return None

            # 3. Now, perform the crucial signature verification using the fetched key.
            jwt.decode(
                token,
                key=device.public_key.public_key,
                algorithms=[device.public_key.algorithm]
            )
            
            # 4. If verification succeeds, fetch related data and update the scope.
            @database_sync_to_async
            def get_elements(dev):
                elements = Element.objects.filter(device=dev)
                return [model_to_dict_updates(e) for e in elements]
            

            elements = await get_elements(device)
            
            scope["device"] = model_to_dict_updates(device)
            scope['element'] = elements
            return scope

        except jwt.InvalidSignatureError:
            logger.error(f"Invalid signature for token corresponding to device_id '{device_id}'.")
            return None
        except jwt.ExpiredSignatureError:
            logger.error(f"Token has expired for device_id '{device_id}'.")
            return None
        except jwt.InvalidTokenError as e:
            # This catches other JWT format errors.
            logger.error(f"Invalid token format: {e}")
            return None
        except Exception as e:
            logger.error(f"An unexpected error occurred during authentication: {e}", exc_info=True)
            return None

# ./migrations/0001_initial.py
# Generated by Django 5.1.1 on 2025-01-24 13:17

import django.core.validators
import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Device',
            fields=[
                ('id', models.UUIDField(default=uuid.UUID('7b14e451-21e4-5412-8d9a-395f0b3a7e52'), editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50)),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='Element',
            fields=[
                ('id', models.UUIDField(default=uuid.UUID('7b14e451-21e4-5412-8d9a-395f0b3a7e52'), editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(max_length=50)),
                ('element_id', models.CharField(max_length=50, unique=True)),
                ('points', models.IntegerField(validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(1000)])),
                ('description', models.TextField()),
            ],
        ),
        migrations.CreateModel(
            name='ElementPermissionsGroup',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('permissions', models.CharField(choices=[('R', 'Read'), ('RC', 'Read and change')], max_length=2)),
                ('element', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='node_red.element')),
                ('group', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='auth.group')),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('group', 'element'), name='unique_group_element')],
            },
        ),
        migrations.CreateModel(
            name='ElementPermissionsUser',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('permissions', models.CharField(choices=[('R', 'Read'), ('RC', 'Read and change')], max_length=2)),
                ('element', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='node_red.element')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'constraints': [models.UniqueConstraint(fields=('user', 'element'), name='unique_user_element')],
            },
        ),
    ]


# ./migrations/0002_jwtpublickey_element_created_at_element_details_and_more.py
# Generated by Django 5.2.6 on 2025-09-29 05:45

import django.db.models.deletion
import django.utils.timezone
import node_red.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('node_red', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='JWTPublicKey',
            fields=[
                ('id', models.UUIDField(default=node_red.models.generate_uuid_public_key, editable=False, primary_key=True, serialize=False)),
                ('name', models.CharField(help_text="A descriptive name for the key (e.g., 'Payment Service Public Key').", max_length=100)),
                ('public_key', models.TextField(help_text='Paste the public key in PEM format here. The system will analyze it.')),
                ('algorithm', models.CharField(blank=True, choices=[('RS256', 'RS256 (Asymmetric, RSA-SHA256)'), ('ES256', 'ES256 (Asymmetric, ECDSA-SHA256)')], editable=False, help_text='The algorithm of the key, detected automatically.', max_length=10)),
                ('key_size', models.PositiveIntegerField(blank=True, editable=False, help_text='The key size (in bits), detected automatically.', null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True, help_text='You can deactivate a key instead of deleting it.')),
            ],
            options={
                'verbose_name': 'JWT Public Key',
                'verbose_name_plural': 'JWT Public Keys',
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddField(
            model_name='element',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='element',
            name='details',
            field=models.JSONField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='element',
            name='device',
            field=models.ForeignKey(default=1, on_delete=django.db.models.deletion.CASCADE, to='node_red.device'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='device',
            name='id',
            field=models.UUIDField(default=node_red.models.generate_uuid_device, editable=False, primary_key=True, serialize=False),
        ),
        migrations.AlterField(
            model_name='element',
            name='description',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='element',
            name='id',
            field=models.UUIDField(default=node_red.models.generate_uuid_element, editable=False, primary_key=True, serialize=False),
        ),
        migrations.CreateModel(
            name='Connections',
            fields=[
                ('id', models.UUIDField(default=node_red.models.generate_uuid_connection, editable=False, primary_key=True, serialize=False)),
                ('details', models.JSONField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('device', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='connections', to='node_red.device')),
            ],
        ),
        migrations.AddField(
            model_name='device',
            name='public_key',
            field=models.ForeignKey(blank=True, help_text='The unique public key that identifies this device.', null=True, on_delete=django.db.models.deletion.SET_NULL, to='node_red.jwtpublickey'),
        ),
    ]


# ./migrations/__init__.py


# ./models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.conf import settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec

import jwt
from datetime import datetime, timedelta
from django.conf import settings
import uuid
from channels.db import database_sync_to_async


def generate_uuid_device():
    return uuid.uuid5(uuid.NAMESPACE_DNS, 'Device'+str(uuid.uuid4()))
def generate_uuid_element():
    return uuid.uuid5(uuid.NAMESPACE_DNS, 'element'+str(uuid.uuid4()))
def generate_uuid_connection():
    return uuid.uuid5(uuid.NAMESPACE_DNS, 'device connection'+str(uuid.uuid4()))
def generate_uuid_public_key():
    return uuid.uuid5(uuid.NAMESPACE_DNS, 'device public key'+str(uuid.uuid4()))


STATUS_CHOICES = [
    ('R', 'Read'),
    ('RC', 'Read and change'),
]

class Device(models.Model):
    """Model representing a device with specific attributes."""
    id = models.UUIDField(primary_key=True, default=generate_uuid_device, editable=False)
    name = models.CharField(max_length=50)
    description = models.TextField()
    public_key = models.ForeignKey('JWTPublicKey', on_delete=models.SET_NULL, null=True, blank=True, help_text="The unique public key that identifies this device.")

class Connections(models.Model):
    id = models.UUIDField(primary_key=True, default=generate_uuid_connection, editable=False)
    device = models.ForeignKey(Device, on_delete=models.CASCADE, related_name='connections')
    details = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Connection for device {self.device.name}"
    
 
class Element(models.Model):
    """Model representing an element with specific attributes."""
    id = models.UUIDField(primary_key=True, default=generate_uuid_element, editable=False)
    name = models.CharField(max_length=50)
    device = models.ForeignKey(Device, on_delete=models.CASCADE)

    element_id = models.CharField(max_length=50, unique=True)
    points = models.IntegerField(
        validators=[MinValueValidator(0), MaxValueValidator(1000)]
    )
    description = models.TextField(null=True, blank=True)
    details = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @database_sync_to_async
    def is_connected(self):
        """Check if the element's device has any connections."""
        return Connections.objects.filter(device=self.device).exists()
       

    def __str__(self) -> str:
        return f"{self.element_id}: {self.name}"

class PermissionManager(models.Manager):
    """Custom manager for handling permission logic for users and groups."""

    def get_user_permission(self, user, element):
        """
        check if the user has permission for the element.
        """
        # Check for direct user permission
        element_permission = ElementPermissionsUser.objects.filter(user=user, element=element).first()
        if element_permission:
            return element_permission


        return None

    def get_max_group_permission(self,user,element):
        """
        Get the maximum permission for a group on an element.
        """
        groups = user.groups.all()
        element_permission = ElementPermissionsGroup.objects.filter(group__in=groups, element=element).order_by('permissions').last()
        if element_permission:
            return element_permission
        return None
    def get_max_permission(self, user, element):
        """
        Get the maximum permission for a user on an element.
        """
        user_permission = self.get_user_permission(user, element)
        group_permission = self.get_max_group_permission(user, element)

        if user_permission and user_permission.permissions == 'RC':
            return user_permission
        if group_permission and group_permission.permissions == 'RC':
            return group_permission
        if user_permission and user_permission.permissions == 'R':
            return user_permission
        if group_permission and group_permission.permissions == 'R':
            return group_permission

        return None
class ElementPermissionsUser(models.Model):
    """Model to represent user permissions for specific elements."""

    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    element = models.ForeignKey(Element, on_delete=models.CASCADE)
    permissions = models.CharField(max_length=2, choices=STATUS_CHOICES)

    objects = models.Manager()  # Default manager
    permission_manager = PermissionManager()  # Custom permission manager

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['user', 'element'], name='unique_user_element')
        ]

    def __str__(self) -> str:
        return f"{self.user} has permission {self.permissions} on {self.element}"

class ElementPermissionsGroup(models.Model):
    """Model to represent group permissions for specific elements."""

    id = models.AutoField(primary_key=True)
    group = models.ForeignKey(Group, on_delete=models.CASCADE)
    element = models.ForeignKey(Element, on_delete=models.CASCADE)
    permissions = models.CharField(max_length=2, choices=STATUS_CHOICES)

    objects = models.Manager()  # Default manager
    permission_manager = PermissionManager()  # Custom permission manager

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['group', 'element'], name='unique_group_element')
        ]

    def __str__(self):
        return f'{self.group} has permission {self.permissions} on {self.element}'
    





class JWTPublicKey(models.Model):
    class Algorithm(models.TextChoices):
        RS256 = 'RS256', 'RS256 (Asymmetric, RSA-SHA256)'
        ES256 = 'ES256', 'ES256 (Asymmetric, ECDSA-SHA256)'
    id = models.UUIDField(primary_key=True, default=generate_uuid_public_key, editable=False)
    name = models.CharField(
        max_length=100,
        help_text="A descriptive name for the key (e.g., 'Payment Service Public Key')."
    )
    public_key = models.TextField(
        help_text="Paste the public key in PEM format here. The system will analyze it."
    )
    algorithm = models.CharField(
        max_length=10,
        choices=Algorithm.choices,
        blank=True,
        editable=False,
        help_text="The algorithm of the key, detected automatically."
    )
    key_size = models.PositiveIntegerField(
        blank=True,
        null=True,
        editable=False,
        help_text="The key size (in bits), detected automatically."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True, help_text="You can deactivate a key instead of deleting it.")

    class Meta:
        verbose_name = "JWT Public Key"
        verbose_name_plural = "JWT Public Keys"
        ordering = ['-created_at']

    def __str__(self):
        algo = self.algorithm or "N/A"
        return f"{self.name} ({algo})"

    def _analyze_and_populate_key_details(self):
        if not self.public_key:
            raise ValidationError("Public key field cannot be empty.")

        try:
            public_key_pem = self.public_key.encode('utf-8')
            public_key_obj = serialization.load_pem_public_key(public_key_pem)

            if isinstance(public_key_obj, rsa.RSAPublicKey):
                self.algorithm = self.Algorithm.RS256
                self.key_size = public_key_obj.key_size
            
            elif isinstance(public_key_obj, ec.EllipticCurvePublicKey):
                if public_key_obj.curve.name == 'secp256r1':
                    self.algorithm = self.Algorithm.ES256
                    self.key_size = public_key_obj.curve.key_size
                else:
                    raise ValidationError(
                        f"Unsupported EC curve: '{public_key_obj.curve.name}'. Only 'secp256r1' (for ES256) is supported."
                    )
            
            else:
                raise ValidationError("Unsupported key type. Only RSA and ECDSA keys are supported.")

        except (ValueError, TypeError) as e:
            raise ValidationError(f"Invalid PEM public key format: {e}")

    def save(self, *args, **kwargs):
        self._analyze_and_populate_key_details()
        super().save(*args, **kwargs)

# ./routing_browser.py
from django.urls import path
from node_red.consumers.browser import BrowserConsumer

websocket_urlpatterns_browser = [
    path("browser/simple/", BrowserConsumer.as_asgi()),
    
    
]


# ./routing_devices.py
from django.urls import path
from .consumers.nodered import NodeRedConsumer

websocket_urlpatterns = [
    path('device/node_red/', NodeRedConsumer.as_asgi()),  # Define your WebSocket URL pattern
]




# ./serializers.py
from rest_framework import serializers
from .models import Device,Element,ElementPermissionsUser,ElementPermissionsGroup

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__' 

class ElementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Element
        fields = '__all__'

class ElementPermissionsUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElementPermissionsUser
        fields = '__all__'

class ElementPermissionsGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = ElementPermissionsGroup
        fields = '__all__'


# ./signals.py
from django.db.models.signals import post_save,post_delete
from django.dispatch import receiver
from .models import Device,Element,ElementPermissionsGroup,ElementPermissionsUser,Connections,JWTPublicKey
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.forms.models import model_to_dict
from django.core.cache import cache
from .middleware import model_to_dict_updates
import logging

logger = logging.getLogger(__name__)

# --------------------------------------------------------------------------
# Helper Function
# --------------------------------------------------------------------------

def _send_group_message(group_name, message_type, payload):
    """
    A centralized helper to send a message to a channel layer group.
    """
    try:
        channel_layer = get_channel_layer()
        message = {
            "type": message_type,
            **payload
        }
        async_to_sync(channel_layer.group_send)(group_name, message)
        logger.debug(f"Sent message type '{message_type}' to group '{group_name}'.")
    except Exception as e:
        logger.error(f"Failed to send message to group '{group_name}': {e}")

# --------------------------------------------------------------------------
# Connection Status Signals
# --------------------------------------------------------------------------

def _notify_elements_connection_status(device, status):
    """
    Notifies all elements of a device about a connection status change.
    """
    # Find all elements associated with the device
    elements = Element.objects.filter(device=device)
    for element in elements:
        _send_group_message(
            group_name=str(element.id),
            message_type="element_connection_status", # Standardized name
            payload={
                "status": status,
                "element_id": str(element.id)
            }
        )
@receiver(post_save, sender=JWTPublicKey)
def on_jwt_public_key_save(sender, instance, created, **kwargs):
    """
    If a JWT public key is created or updated, notify all devices using this key to restart connection.
    """
    # Find all devices associated with this public key
    devices = Device.objects.filter(public_key=instance)
    for device in devices:
        _notify_elements_connection_status(device, "disconnected")
@receiver(post_save, sender=Connections)
def on_connection_created(sender, instance, created, **kwargs):
    """
    When a new connection is created, notify relevant elements that the device is 'connected'.
    """
    if created:
        _notify_elements_connection_status(instance.device, "connected")
    else:
        _notify_elements_connection_status(instance.device, "disconnected")

@receiver(post_delete, sender=Connections)
def on_connection_deleted(sender, instance, **kwargs):
    """
    When a connection is deleted, check if it was the last one.
    If so, notify elements that the device is 'disconnected'.
    """
    # Check if any other connections for this device still exist
    logger.debug(f"Connection deleted for device {instance.device.id}. Checking remaining connections.")
    is_last_connection = not Connections.objects.filter(device=instance.device).exists()
    if is_last_connection:
        _notify_elements_connection_status(instance.device, "disconnected")

# --------------------------------------------------------------------------
# Device & Element Model Sync Signals
# --------------------------------------------------------------------------

@receiver(post_save, sender=Device)
def on_device_save(sender, instance, created, **kwargs):
    """
    Forwards device updates to the corresponding device group.
    """
    _send_group_message(
        group_name=str(instance.id),
        message_type="device_updates",
        payload={
            "message": model_to_dict_updates(instance),
            "state": "update"
        }
    )

@receiver(post_delete, sender=Device)
def on_device_delete(sender, instance, **kwargs):
    """
    Notifies the device group that the device has been deleted.
    """
    _send_group_message(
        group_name=str(instance.id),
        message_type="device_updates",
        payload={
            "message": model_to_dict_updates(instance),
            "state": "delete"
        }
    )

@receiver(post_save, sender=Element)
def on_element_save(sender, instance, created, **kwargs):
    """
    Forwards element creations or updates to the parent device group.
    """
    state = "create" if created else "update"
    _send_group_message(
        group_name=str(instance.device_id),
        message_type="elements_updates",
        payload={
            "message": model_to_dict_updates(instance),
            "state": state
        }
    )

@receiver(post_delete, sender=Element)
def on_element_delete(sender, instance, **kwargs):
    """
    Forwards element deletions to the parent device group and clears its cache.
    """
    _send_group_message(
        group_name=str(instance.device_id),
        message_type="elements_updates",
        payload={
            "message": model_to_dict_updates(instance),
            "state": "delete"
        }
    )
    # Clear any associated cache for this element
    cache.delete(f"cache:{instance.id}")
    logger.info(f"Cleared cache for deleted element {instance.id}")

# --------------------------------------------------------------------------
# Permissions Sync Signals
# --------------------------------------------------------------------------

def _handle_permission_change(instance, state):
    """
    A generic handler for permission model changes (User and Group).
    Notifies the specific permission group about the update.
    """
    # Standardize the group name to match the consumer logic
    group_name = f"perm_{instance.id}"
    _send_group_message(
        group_name=group_name,
        message_type="permissions_updates",
        payload={
            "message": model_to_dict_updates(instance),
            "state": state
        }
    )

@receiver(post_save, sender=ElementPermissionsUser)
@receiver(post_save, sender=ElementPermissionsGroup)
def on_permission_save(sender, instance, created, **kwargs):
    """
    Handles save events for both User and Group permissions.
    """
    state = "create" if created else "update"
    _handle_permission_change(instance, state)

@receiver(post_delete, sender=ElementPermissionsUser)
@receiver(post_delete, sender=ElementPermissionsGroup)
def on_permission_delete(sender, instance, **kwargs):
    """
    Handles delete events for both User and Group permissions.
    """
    _handle_permission_change(instance, "delete")


# ./templatetags/filters.py
import uuid
from django import template

register = template.Library()

@register.filter(name="append_uuid")
def append_uuid(value):
    return f"{value}_{uuid.uuid4()}"

# ./templatetags/__init__.py


# ./tests.py
from django.test import TestCase

# Create your tests here.


# ./urls.py
# myapp/urls.py

from django.urls import path
from . import views

urlpatterns = [
    path("",views.test_view,name="test_view"),
    path("test/",views.tester_view,name="guage_view"),
]


# ./views.py

# Create your views here.
from django.shortcuts import render,HttpResponse
from .models import Device,Element
def test_view(request):
    return render(request,'test.html')
def tester_view(request):
    
    elements = Element.objects.all().order_by('element_id')

    return render(request,r'cards/templates/test_guage.html',{'elements':elements})

