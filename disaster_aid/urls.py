from django.urls import path
from .views import (
    home, login_view, register_view, logout_view,
    report_incident, dashboard, incident_detail,
    admin_dashboard, verify_incident, deny_incident,
    inventory_list, update_inventory, distribution_list, approve_distribution, complete_distribution, distribution_detail,
    distribution_management, export_distributions,
    recent_incidents_api, mark_notification_read,
    report_list, export_report,
    create_alert, manage_alerts, activate_alert, deactivate_alert,
    # Evacuation Center views
    evacuation_center_list, evacuation_center_detail, create_evacuation_center, update_evacuation_center,
    activate_evacuation_center, deactivate_evacuation_center, close_evacuation_center,
    add_evacuee, evacuee_departure, generate_evacuation_report,
    # Admin views
    comprehensive_view, consolidated_table_view, export_consolidated_pdf,
    # User Management views
    user_management
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
    path('complete-distribution/<int:distribution_id>/', complete_distribution, name='complete_distribution'),
    path('distribution-detail/<int:distribution_id>/', distribution_detail, name='distribution_detail'),
    path('distribution-management/', distribution_management, name='distribution_management'),
    path('export-distributions/', export_distributions, name='export_distributions'),

    # Report URLs
    path('reports/', report_list, name='report_list'),
    path('export-report/', export_report, name='export_report'),

    # API URLs for HTMX
    path('api/recent-incidents/', recent_incidents_api, name='recent_incidents_api'),

    # Notification URLs
    path('notifications/mark-read/<int:notification_id>/', mark_notification_read, name='mark_notification_read'),

    # Disaster Alert URLs
    path('alerts/create/', create_alert, name='create_alert'),
    path('alerts/manage/', manage_alerts, name='manage_alerts'),
    path('alerts/activate/<int:alert_id>/', activate_alert, name='activate_alert'),
    path('alerts/deactivate/<int:alert_id>/', deactivate_alert, name='deactivate_alert'),

    # Evacuation Center URLs
    path('evacuation-centers/', evacuation_center_list, name='evacuation_center_list'),
    path('evacuation-centers/<int:center_id>/', evacuation_center_detail, name='evacuation_center_detail'),
    path('evacuation-centers/create/', create_evacuation_center, name='create_evacuation_center'),
    path('evacuation-centers/<int:center_id>/update/', update_evacuation_center, name='update_evacuation_center'),
    path('evacuation-centers/<int:center_id>/activate/', activate_evacuation_center, name='activate_evacuation_center'),
    path('evacuation-centers/<int:center_id>/deactivate/', deactivate_evacuation_center, name='deactivate_evacuation_center'),
    path('evacuation-centers/<int:center_id>/close/', close_evacuation_center, name='close_evacuation_center'),
    path('evacuation-centers/<int:center_id>/add-evacuee/', add_evacuee, name='add_evacuee'),
    path('evacuees/<int:evacuee_id>/departure/', evacuee_departure, name='evacuee_departure'),
    path('evacuation-centers/<int:center_id>/report/', generate_evacuation_report, name='generate_evacuation_report'),

    # Admin URLs
    path('comprehensive-data/', comprehensive_view, name='comprehensive_view'),
    path('consolidated-table/', consolidated_table_view, name='consolidated_table_view'),
    path('export-consolidated-pdf/', export_consolidated_pdf, name='export_consolidated_pdf'),

    # User Management URLs
    path('users/', user_management, name='user_management'),
]

# Add media URL patterns in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
