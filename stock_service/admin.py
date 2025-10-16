# stock_service/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from .models import (
    Society, SocietyUser, StockObjectKind, StockObject, Drawer, StockObjectDrawerPlacement,
    StockMovement, ObjectUser, StockUsage, RefillSchedule
)

# --- Import-Export Resources ---

class SocietyResource(resources.ModelResource):
    class Meta:
        model = Society
        fields = ('id', 'name', 'slug', 'is_active', 'subscription_level', 'can_manage_drawers', 'shows_drawers_in_list', 'created_at', 'updated_at',)
        export_order = fields

class SocietyUserResource(resources.ModelResource):
    class Meta:
        model = SocietyUser
        fields = ('id', 'user', 'society', 'is_society_admin',)
        export_order = fields

class StockObjectKindResource(resources.ModelResource):
    class Meta:
        model = StockObjectKind
        fields = ('id', 'society', 'name', 'description',)
        export_order = fields

class StockObjectResource(resources.ModelResource):
    class Meta:
        model = StockObject
        fields = ('id', 'society', 'kind', 'name', 'description', 'current_quantity', 'minimum_quantity', 'unit', 'location_description', 'is_active', 'created_at', 'updated_at',)
        export_order = fields

class DrawerResource(resources.ModelResource):
    class Meta:
        model = Drawer
        fields = ('id', 'society', 'cabinet_name', 'drawer_letter_x', 'drawer_number_y', 'description',)
        export_order = fields

class StockObjectDrawerPlacementResource(resources.ModelResource):
    class Meta:
        model = StockObjectDrawerPlacement
        fields = ('id', 'stock_object', 'drawer', 'quantity',)
        export_order = fields

class StockMovementResource(resources.ModelResource):
    class Meta:
        model = StockMovement
        fields = ('id', 'society', 'stock_object', 'movement_type', 'quantity', 'moved_by', 'timestamp', 'notes', 'drawer_involved',)
        export_order = fields

class ObjectUserResource(resources.ModelResource):
    class Meta:
        model = ObjectUser
        fields = ('id', 'society', 'name', 'contact_info', 'notes',)
        export_order = fields

class StockUsageResource(resources.ModelResource):
    class Meta:
        model = StockUsage
        fields = ('id', 'society', 'stock_object', 'object_user', 'quantity_used', 'start_date', 'end_date', 'notes', 'logged_by', 'logged_at',)
        export_order = fields

class RefillScheduleResource(resources.ModelResource):
    class Meta:
        model = RefillSchedule
        fields = ('id', 'society', 'stock_object', 'scheduled_date', 'quantity_to_refill', 'is_completed', 'completed_date', 'notes', 'created_at', 'updated_at',)
        export_order = fields

# --- Admin Classes ---
class SocietyUserInline(admin.TabularInline):
    model = SocietyUser
    extra = 1
    fields = ('user', 'is_society_admin',)
    
@admin.register(Society)
class SocietyAdmin(ImportExportModelAdmin):
    resource_class = SocietyResource
    list_display = ('name', 'slug', 'is_active', 'subscription_level', 'can_manage_drawers', 'shows_drawers_in_list', 'created_at',)
    list_filter = ('is_active', 'subscription_level', 'can_manage_drawers', 'shows_drawers_in_list',)
    search_fields = ('name', 'slug',)
    prepopulated_fields = {'slug': ('name',)}
    inlines = [SocietyUserInline]
    fieldsets = (
        (None, {'fields': ('name', 'slug', 'is_active', 'subscription_level')}),
        (_('Drawer Management Settings'), {'fields': ('can_manage_drawers', 'shows_drawers_in_list',), 'classes': ('collapse',)}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',), 'description': _("Automatically generated timestamps.")}),
    )
    readonly_fields = ('created_at', 'updated_at',)





@admin.register(SocietyUser)
class SocietyUserAdmin(ImportExportModelAdmin):
    resource_class = SocietyUserResource
    list_display = ('user', 'society', 'is_society_admin',)
    list_filter = ('is_society_admin', 'society',)
    search_fields = ('user__username', 'society__name',)
    raw_id_fields = ('user', 'society',)


@admin.register(StockObjectKind)
class StockObjectKindAdmin(ImportExportModelAdmin):
    resource_class = StockObjectKindResource
    list_display = ('name', 'society', 'description',)
    list_filter = ('society',)
    search_fields = ('name', 'society__name',)
    raw_id_fields = ('society',)


@admin.register(StockObject)
class StockObjectAdmin(ImportExportModelAdmin):
    resource_class = StockObjectResource
    list_display = ('name', 'society', 'kind', 'current_quantity', 'minimum_quantity', 'unit', 'is_active',)
    list_filter = ('society', 'kind', 'is_active',)
    search_fields = ('name', 'description', 'society__name',)
    raw_id_fields = ('society', 'kind',)
    fieldsets = (
        (None, {'fields': ('society', 'kind', 'name', 'description', 'unit', 'is_active')}),
        (_('Quantity Information'), {'fields': ('current_quantity', 'minimum_quantity')}),
        (_('Location'), {'fields': ('location_description',)}),
        (_('Timestamps'), {'fields': ('created_at', 'updated_at'), 'classes': ('collapse',), 'description': _("Automatically generated timestamps.")}),
    )
    readonly_fields = ('created_at', 'updated_at',)


@admin.register(Drawer)
class DrawerAdmin(ImportExportModelAdmin):
    resource_class = DrawerResource
    list_display = ('cabinet_name', 'drawer_letter_x', 'drawer_number_y', 'society', 'description',)
    list_filter = ('society', 'cabinet_name',)
    search_fields = ('cabinet_name', 'drawer_letter_x', 'drawer_number_y', 'society__name',)
    raw_id_fields = ('society',)


@admin.register(StockObjectDrawerPlacement)
class StockObjectDrawerPlacementAdmin(ImportExportModelAdmin):
    resource_class = StockObjectDrawerPlacementResource
    list_display = ('stock_object', 'drawer', 'quantity',)
    list_filter = ('stock_object__society', 'drawer__cabinet_name',)
    search_fields = ('stock_object__name', 'drawer__cabinet_name', 'drawer__drawer_letter_x', 'drawer__drawer_number_y',)
    raw_id_fields = ('stock_object', 'drawer',)


@admin.register(StockMovement)
class StockMovementAdmin(ImportExportModelAdmin):
    resource_class = StockMovementResource
    list_display = ('stock_object', 'movement_type', 'quantity', 'moved_by', 'timestamp', 'society',)
    list_filter = ('society', 'movement_type', 'stock_object', 'moved_by',)
    search_fields = ('stock_object__name', 'notes', 'moved_by__username', 'society__name',)
    raw_id_fields = ('society', 'stock_object', 'moved_by', 'drawer_involved',)
    readonly_fields = ('timestamp',)


@admin.register(ObjectUser)
class ObjectUserAdmin(ImportExportModelAdmin):
    resource_class = ObjectUserResource
    list_display = ('name', 'society', 'contact_info',)
    list_filter = ('society',)
    search_fields = ('name', 'contact_info', 'society__name',)
    raw_id_fields = ('society',)


@admin.register(StockUsage)
class StockUsageAdmin(ImportExportModelAdmin):
    resource_class = StockUsageResource
    list_display = ('stock_object', 'object_user', 'quantity_used', 'start_date', 'end_date', 'logged_by', 'society',)
    list_filter = ('society', 'stock_object', 'object_user', 'logged_by',)
    search_fields = ('stock_object__name', 'object_user__name', 'notes', 'society__name',)
    raw_id_fields = ('society', 'stock_object', 'object_user', 'logged_by',)
    readonly_fields = ('logged_at',)


@admin.register(RefillSchedule)
class RefillScheduleAdmin(ImportExportModelAdmin):
    resource_class = RefillScheduleResource
    list_display = ('stock_object', 'scheduled_date', 'quantity_to_refill', 'is_completed', 'completed_date', 'society',)
    list_filter = ('society', 'is_completed', 'scheduled_date',)
    search_fields = ('stock_object__name', 'notes', 'society__name',)
    raw_id_fields = ('society', 'stock_object',)
    readonly_fields = ('created_at', 'updated_at',)