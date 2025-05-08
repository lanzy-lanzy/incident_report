from django.urls import path
from .views import (
    home, login_view, register_view, logout_view,
    report_incident, dashboard, incident_detail,
    admin_dashboard, verify_incident, deny_incident,
    inventory_list, update_inventory, distribution_list, approve_distribution,
    recent_incidents_api, mark_notification_read
)
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Authentication URLs
    path('', home, name='home'),
    path('login/', login_view, name='login'),
    path('register/', register_view, name='register'),
    path('logout/', logout_view, name='logout'),

    # Incident Reporting URLs
    path('report/', report_incident, name='report_incident'),
    path('incident/<int:incident_id>/', incident_detail, name='incident_detail'),

    # Dashboard URLs
    path('dashboard/', dashboard, name='dashboard'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('verify-incident/<int:incident_id>/', verify_incident, name='verify_incident'),
    path('deny-incident/<int:incident_id>/', deny_incident, name='deny_incident'),

    # Inventory Management URLs
    path('inventory/', inventory_list, name='inventory_list'),
    path('inventory/update/<int:inventory_id>/', update_inventory, name='update_inventory'),
    path('distributions/', distribution_list, name='distribution_list'),
    path('approve-distribution/<int:distribution_id>/', approve_distribution, name='approve_distribution'),

    # API URLs for HTMX
    path('api/recent-incidents/', recent_incidents_api, name='recent_incidents_api'),

    # Notification URLs
    path('notifications/mark-read/<int:notification_id>/', mark_notification_read, name='mark_notification_read'),
]

# Add media URL patterns in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
