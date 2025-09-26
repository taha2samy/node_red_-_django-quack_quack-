from django.contrib import admin
from .models import Device, Element, ElementPermissionsUser, ElementPermissionsGroup,Connections,JWTSigningKey

# Register Device model to the admin panel
class DeviceAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'description', 'token')
    search_fields = ('name', 'description')
    readonly_fields = ('id', 'token')

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

@admin.register(JWTSigningKey)
class JWTSigningKeyAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'algorithm', 'is_active', 'created_at')
    list_filter = ('algorithm', 'is_active', 'user')
    search_fields = ('name', 'user__username')
    
    # Make key fields read-only after they have been created to prevent accidental changes
    def get_readonly_fields(self, request, obj=None):
        if obj:  # If the object already exists
            return ('private_key', 'public_key', 'algorithm', 'key_size', 'user')
        return () # Otherwise, all fields are editable
