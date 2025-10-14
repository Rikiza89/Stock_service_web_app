# stock_service/admin.py
from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Society, User, StockObjectKind, StockObject, Drawer, StockObjectDrawerPlacement,
    StockMovement, ObjectUser, StockUsage, RefillSchedule
)
from django.contrib.auth.models import User as AuthUser # Import the built-in user model for unregistering

# --- Import-Export Resources ---
# 💡 修正ステップ: デフォルトのUserAdminを先に解除する
# get_user_model() が返したカスタムUserモデルが、デフォルトのUserAdminで登録されていないかチェックし、解除する
try:
    admin.site.unregister(User) 
except admin.sites.NotRegistered:
    # 既に登録解除されているか、元々登録されていなかった場合は何もしない
    pass

class SocietyResource(resources.ModelResource):
    class Meta:
        model = Society
        fields = ('id', 'name', 'slug', 'is_active', 'subscription_level', 'can_manage_drawers', 'shows_drawers_in_list', 'created_at', 'updated_at',)
        export_order = fields

class UserResource(resources.ModelResource):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined', 'last_login', 'society', 'is_society_admin',)
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

# Society モデルの管理サイト登録 (確認用)
@admin.register(Society)
class SocietyAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_active', 'created_at')
    search_fields = ('name',)
    list_filter = ('is_active',)

# カスタムUserモデルの管理クラスを定義
@admin.register(User) 
class UserAdmin(BaseUserAdmin):
    # 既存のフィールドセットに 'society' を追加
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email', 'society')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # ユーザー追加フォームのフィールドセットに 'society' を追加
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'email', 'first_name', 'last_name', 'society', 'password', 'password2'),
        }),
    )
    
    # 【修正箇所 1】: BaseUserAdmin の list_display を拡張し、society を追加
    list_display = BaseUserAdmin.list_display + ('society', 'is_society_admin',)
    
    # 【修正箇所 2】: BaseUserAdmin の list_filter を拡張し、society を追加
    # society は ForeignKey フィールドなので、そのまま list_filter に追加可能です
    list_filter = BaseUserAdmin.list_filter + ('society',) 
    
    # 検索フィールドに追加 (これは問題ありません)
    search_fields = ('username', 'first_name', 'last_name', 'email')

@admin.register(StockObjectKind)
class StockObjectKindAdmin(ImportExportModelAdmin):
    resource_class = StockObjectKindResource
    list_display = ('name', 'society', 'description',)
    list_filter = ('society',)
    search_fields = ('name', 'society__name',)
    raw_id_fields = ('society',) # Use raw_id_fields for ForeignKey to improve performance with many societies


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