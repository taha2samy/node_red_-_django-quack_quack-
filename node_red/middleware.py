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