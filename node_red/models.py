from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.conf import settings
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa, ec
import os
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
    description = models.TextField(null=True, blank=True)
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
        return f"{self.id}: {self.name}"
    
class ElementDetailsStyle(models.Model):
    element = models.ForeignKey(Element, on_delete=models.CASCADE, related_name='style_details')
    name = models.CharField(max_length=100)
    details = models.JSONField(null=True, blank=True)


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