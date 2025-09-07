from django.contrib import admin
from django.urls import path, include
from loyalty.api import process_customer_purchase, get_customer_info
from loyalty.cashier_api import process_discount_code, validate_discount_code, validate_phone_number, process_phone_purchase, process_receipt_auto
from loyalty.views import cashier_interface, login_view, logout_view, admin_panel, admin_stats_api, admin_users_api, admin_codes_api, admin_generate_code_api, admin_analytics_api, admin_export_api, admin_broadcast_api

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', login_view, name='home'),
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('cashier/', cashier_interface, name='cashier_interface'),
    path('api/process-purchase/', process_customer_purchase, name='process_purchase'),
    path('api/customer/<str:phone_number>/', get_customer_info, name='customer_info'),
    path('api/cashier/process-code/', process_discount_code, name='process_discount_code'),
    path('api/cashier/validate-code/<str:code>/', validate_discount_code, name='validate_discount_code'),
    path('api/cashier/validate-phone/<str:phone_number>/', validate_phone_number, name='validate_phone_number'),
    path('api/cashier/process-phone/', process_phone_purchase, name='process_phone_purchase'),
    path('api/cashier/process-receipt-auto/', process_receipt_auto, name='process_receipt_auto'),
    
    # Admin panel URLs
    path('admin-panel/', admin_panel, name='admin_panel'),
    path('api/admin/stats/', admin_stats_api, name='admin_stats_api'),
    path('api/admin/users/', admin_users_api, name='admin_users_api'),
    path('api/admin/codes/', admin_codes_api, name='admin_codes_api'),
    path('api/admin/generate-code/', admin_generate_code_api, name='admin_generate_code_api'),
    path('api/admin/analytics/', admin_analytics_api, name='admin_analytics_api'),
    path('api/admin/export/', admin_export_api, name='admin_export_api'),
    path('api/admin/broadcast/', admin_broadcast_api, name='admin_broadcast_api'),
]