from django.contrib import admin
from .models import (
    DisasterType,
    DistributionType,
    Inventory,
    ReporterProfile,
    IncidentReport,
    IncidentDistribution,
    UserNotification,
    Municipality,
    Barangay,
    DisasterAlert
)

class ReporterProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'profile_image')
    search_fields = ('user__username', 'user__email')

class IncidentReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'barangay', 'location', 'disaster_type', 'reporter', 'date_reported', 'is_verified')
    list_filter = ('disaster_type', 'is_verified', 'date_reported', 'barangay__municipality')
    search_fields = ('title', 'description', 'location', 'reporter__username', 'barangay__name')
    date_hierarchy = 'date_reported'

class IncidentDistributionAdmin(admin.ModelAdmin):
    list_display = ('incident', 'distribution_type', 'quantity_requested', 'quantity_approved', 'is_fulfilled')
    list_filter = ('is_fulfilled', 'distribution_type')
    search_fields = ('incident__title', 'distribution_type__name')

class InventoryAdmin(admin.ModelAdmin):
    list_display = ('item', 'quantity_available')
    search_fields = ('item__name',)

class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'notification_type', 'title', 'created_at', 'is_read')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'title', 'message')
    date_hierarchy = 'created_at'

class MunicipalityAdmin(admin.ModelAdmin):
    list_display = ('name', 'psgc_code')
    search_fields = ('name', 'psgc_code')

class BarangayAdmin(admin.ModelAdmin):
    list_display = ('name', 'municipality', 'psgc_code')
    list_filter = ('municipality',)
    search_fields = ('name', 'psgc_code')


class DisasterAlertAdmin(admin.ModelAdmin):
    list_display = ('title', 'severity', 'created_by', 'created_at', 'is_active')
    list_filter = ('severity', 'is_active', 'created_at')
    search_fields = ('title', 'message')
    date_hierarchy = 'created_at'



# Register models
admin.site.register(DisasterType)
admin.site.register(DistributionType)
admin.site.register(Inventory, InventoryAdmin)
admin.site.register(ReporterProfile, ReporterProfileAdmin)
admin.site.register(IncidentReport, IncidentReportAdmin)
admin.site.register(IncidentDistribution, IncidentDistributionAdmin)
admin.site.register(UserNotification, UserNotificationAdmin)
admin.site.register(Municipality, MunicipalityAdmin)
admin.site.register(Barangay, BarangayAdmin)
admin.site.register(DisasterAlert, DisasterAlertAdmin)
