from django.urls import path
from . import views
from django.utils.translation import gettext_lazy as _
from .views import (
    ObjectUserListView, ObjectUserCreateView, ObjectUserUpdateView, ObjectUserDeleteView,StockObjectKindUpdateView, StockObjectKindDeleteView, DrawerUpdateView, DrawerDeleteView,
    UserListView,
    UserCreateView,
    UserUpdateView,
    UserDeleteView,
)
app_name = 'stock_service'

urlpatterns = [
    # --- NEW: User Management URLs ---
    path('users/', UserListView.as_view(), name='user_list'),
    path('users/create/', UserCreateView.as_view(), name='user_create'),
    path('users/<int:pk>/update/', UserUpdateView.as_view(), name='user_update'),
    path('users/<int:pk>/delete/', UserDeleteView.as_view(), name='user_delete'),

    # 認証関連
    path('login_stock_service/', views.custom_login_stock_service, name='custom_login_stock_service'),
    path('logout_stock_service/', views.custom_logout_stock_service, name='custom_logout_stock_service'),
    path('register_society_stock_service/', views.register_society_stock_service, name='register_society_stock_service'),
    path('pricing_stock_service/', views.pricing_stock_service, name='pricing_stock_service'),
    path('fake-payment/', views.fake_payment_view, name='fake_payment_stock_service'), # NEW URL

    # ホーム
    path('', views.app_home_stock_service, name='app_home_stock_service'),

    # 在庫品目関連
    path('stock_objects_stock_service/', views.stock_object_list_stock_service, name='stock_object_list_stock_service'),
    path('stock_objects/add_stock_service/', views.add_stock_object_stock_service, name='add_stock_object_stock_service'),
    path('stock_objects/<uuid:pk>_stock_service/', views.stock_object_detail_stock_service, name='stock_object_detail_stock_service'),
    path('stock_objects/<uuid:pk>/update_stock_service/', views.update_stock_object_stock_service, name='update_stock_object_stock_service'),
    path('stock_objects/<uuid:pk>/delete_stock_service/', views.delete_stock_object_stock_service, name='delete_stock_object_stock_service'),

    # Stock Object Kind Management URLs
    path('stock-kinds/', views.stock_object_kind_list_stock_service, name='stock_object_kind_list_stock_service'),
    path('stock-kinds/<int:pk>/update/', StockObjectKindUpdateView.as_view(), name='stock_object_kind_update'),
    path('stock-kinds/<int:pk>/delete/', StockObjectKindDeleteView.as_view(), name='stock_object_kind_delete'),

    # 在庫移動関連
    path('stock_out_stock_service/', views.stock_out_stock_service, name='stock_out_stock_service'),
    path('stock_in_stock_service/', views.stock_in_stock_service, name='stock_in_stock_service'),
    path('stock_movements_stock_service/', views.stock_movement_log_stock_service, name='stock_movement_log_stock_service'),

    # オブジェクトユーザー利用ログ関連
    path('object_user_usage_log_stock_service/', views.object_user_usage_log_stock_service, name='object_user_usage_log_stock_service'),
    path('add_stock_usage_stock_service/', views.add_stock_usage_stock_service, name='add_stock_usage_stock_service'),

    # 補充関連
    path('refill_prediction_stock_service/', views.refill_prediction_stock_service, name='refill_prediction_stock_service'),
    path('refill_scheduler_stock_service/', views.refill_scheduler_stock_service, name='refill_scheduler_stock_service_general'),
    path('refill_scheduler/<uuid:pk>/complete_stock_service/', views.complete_refill_stock_service, name='complete_refill_stock_service'),
    path('refill_scheduler_stock_service/<uuid:stock_object_pk>/', views.refill_scheduler_stock_service, name='refill_scheduler_stock_service'),

    # 引き出し管理関連
    path('manage_drawers_stock_service/', views.manage_drawers_stock_service, name='manage_drawers_stock_service'),
    # Drawer Management URLs
    path('drawers/', views.manage_drawers_stock_service, name='manage_drawers_stock_service'),
    path('drawers/<uuid:pk>/update/', DrawerUpdateView.as_view(), name='drawer_update'), # UUIDFieldのため<uuid:pk>
    path('drawers/<uuid:pk>/delete/', DrawerDeleteView.as_view(), name='drawer_delete'), # UUIDFieldのため<uuid:pk>

    path('assign_stock_to_drawer_stock_service/', views.assign_stock_to_drawer_stock_service, name='assign_stock_to_drawer_stock_service'),

    # 社会設定
    path('society_settings_stock_service/', views.society_settings_stock_service, name='society_settings_stock_service'),

    # 在庫品目種類管理
    path('stock_object_kinds_stock_service/', views.stock_object_kind_list_stock_service, name='stock_object_kind_list_stock_service'),

    path('profile/', views.user_profile_view, name='user_profile_stock_service'),

    # NEW: ObjectUser Management URLs
    path('objectusers/', ObjectUserListView.as_view(), name='objectuser_list'),
    path('objectusers/create/', ObjectUserCreateView.as_view(), name='objectuser_create'),
    path('objectusers/<uuid:pk>/update/', ObjectUserUpdateView.as_view(), name='objectuser_update'), # UUIDFieldのためpkをuuidで定義
    path('objectusers/<uuid:pk>/delete/', ObjectUserDeleteView.as_view(), name='objectuser_delete'), # UUIDFieldのためpkをuuidで定義

]
