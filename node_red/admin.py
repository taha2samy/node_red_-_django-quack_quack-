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
