from django.db.models.signals import post_save,post_delete
from django.dispatch import receiver
from .models import Device,Element,ElementPermissionsGroup,ElementPermissionsUser,Connections
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

@receiver(post_save, sender=Connections)
def on_connection_created(sender, instance, created, **kwargs):
    """
    When a new connection is created, notify relevant elements that the device is 'connected'.
    """
    if created:
        _notify_elements_connection_status(instance.device, "connected")

@receiver(post_delete, sender=Connections)
def on_connection_deleted(sender, instance, **kwargs):
    """
    When a connection is deleted, check if it was the last one.
    If so, notify elements that the device is 'disconnected'.
    """
    # Check if any other connections for this device still exist
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
