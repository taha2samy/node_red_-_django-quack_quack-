from django.db.models.signals import post_save,post_delete
from django.dispatch import receiver
from .models import Device,Element,ElementPermissionsGroup,ElementPermissionsUser,Connections
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from django.forms.models import model_to_dict
from django.core.cache import cache
from .middleware import model_to_dict_updates

@receiver(post_save, sender=Connections)
def track_connection_new(sender, instance, created, **kwargs):
    if created:
        elements = Element.objects.filter(device=instance.device)  
        channel_layer = get_channel_layer()
        for element in elements:
            async_to_sync(channel_layer.group_send)(
                str(element.id), 
                {
                    "type": "check_connection_element",
                    "status": "connected",
                    "element_id": str(element.id) 
                }
            )
@receiver(post_delete, sender=Connections)
def track_connection_new(sender, instance, **kwargs):
    elements = Element.objects.filter(device=instance.device)  
    
    channel_layer = get_channel_layer()
    for element in elements:
        async_to_sync(channel_layer.group_send)(
            str(element.id),  
            {
                "type": "check_connection_element",
                "status": "disconnected",
                "element_id": str(element.id)  
            }
        )


@receiver(post_save, sender=Device)
def device_post_save(sender, instance, created, **kwargs):
    state="update"
    channel_layer = get_channel_layer()
    message = model_to_dict_updates(instance)
    async_to_sync(channel_layer.group_send)(
        str(instance.id), 
        {
            "type": "device_updates",
            "message": message,
            "state":state
        }
    )
@receiver(post_delete,sender=Device)
def device_post_delete(sender, instance,**kwargs):
    state="delete"
    message=model_to_dict_updates(instance)
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        str(instance.id), 
        {
            "type": "device_updates",
            "message": message,
            "state":state
        }
    )
    pass

@receiver(post_save,sender=Element)
def element_post_save(sender, instance, created, **kwargs):
    if created:
        state="create"
    else:
        state="update"
    channel_layer = get_channel_layer()
    message = model_to_dict_updates(instance)
    async_to_sync(channel_layer.group_send)(
        str(message['device']), 
        {
            "type": "elements_updates",
            "message": message,
            "state":state
        }
    )
@receiver(post_delete,sender=Element)
def element_post_delete(sender,instance,**kwargs):
    state="delete"
    channel_layer = get_channel_layer()
    message=model_to_dict_updates(instance)
    async_to_sync(channel_layer.group_send)(
        str(message['device']), 
        {
            "type": "elements_updates",
            "message": message,
            "state":state
        }
    )
    cache.delete(f"{instance.id}cache")
    pass
@receiver(post_save,sender=ElementPermissionsUser)
def element_permissions_user_post_save(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    message = model_to_dict_updates(instance)
    async_to_sync(channel_layer.group_send)(
        f"{instance.id}{instance._meta.model_name}", 
        {
            "type": "permissions_updates",
            "message": message,
            "state":"update",
            "channel":f"{instance.id}{instance._meta.model_name}"
        }
    )


@receiver(post_save,sender=ElementPermissionsGroup)
def element_permissions_group_post_save(sender, instance, created, **kwargs):
    channel_layer = get_channel_layer()
    message = model_to_dict_updates(instance)
    async_to_sync(channel_layer.group_send)(
        f"{instance.id}{instance._meta.model_name}", 
        {
            "type": "permissions_updates",
            "message": message,
            "state":"update",
            "channel":f"{instance.id}{instance._meta.model_name}"
        }
    )
@receiver(post_delete,sender=ElementPermissionsUser)
def element_permissions_user_post_delete(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    message = model_to_dict_updates(instance)
    async_to_sync(channel_layer.group_send)(
        f"{instance.id}{instance._meta.model_name}", 
        {
            "type": "permissions_updates",
            "message": message,
            "state":"delete",
            "channel":f"{instance.id}{instance._meta.model_name}"
        }
    )
@receiver(post_delete,sender=ElementPermissionsGroup)
def element_permissions_group_post_delete(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    message = model_to_dict_updates(instance)
    async_to_sync(channel_layer.group_send)(
        f"{instance.id}{instance._meta.model_name}", 
        {
            "type": "permissions_updates",
            "message": message,
            "state":"delete",
            "channel":f"{instance.id}{instance._meta.model_name}"
        }
    )
    pass

@receiver(post_delete,sender=Connections)
def connections_post_delete(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    message = model_to_dict_updates(instance)
    async_to_sync(channel_layer.group_send)(
        f"{instance.device.id}", 
        {
            "type": "connections_updates",
            "message": message,
            "channel":f"{instance.id}",
            "state":"delete"
        }
    )
    pass