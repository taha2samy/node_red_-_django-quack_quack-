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
                auth = {
                    "user_id": payload.get("auth", {}).get("user_id", "coming from Device"),
                    "username": payload.get("auth", {}).get("username", "coming from Device")
                }
                # Validate that the element_id belongs to the connected device
                if element_id not in self.elements_ids:
                    logger.warning(
                        f"Device {self.device.get('id')} sent data for an unauthorized element: {element_id}"
                    )
                    return
  
                self._update_element_cache(element_id, message,auth)
                
                await self.channel_layer.group_send(
                    element_id,
                    {
                        'type': 'forward_element_message',
                        'element_id': element_id,
                        'message': message,
                        'origin_channel': self.channel_name,
                        "auth": auth
             
                  
                        
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
                    "auth": {
                        "user_id": event["auth"].get("user_id", "coming from Device"),
                        "username": event["auth"].get("username", "coming from Device")
                    }
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

    def _update_element_cache(self, element_id, message, auth):
        """Updates the cache for a given element with a new message."""
        element_data = self.elements_data.get(element_id, {})
        cache_key = f"cache:{element_id}"
        # Provide a default maxlen for the deque
        max_points = element_data.get('points', 100)
        queue = cache.get(cache_key, deque(maxlen=max_points))
        queue.append({"message": message, "auth": auth})
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