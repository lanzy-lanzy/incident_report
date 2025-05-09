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
    DisasterAlert,
    EvacuationCenter,
    Evacuee
)

class ReporterProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'profile_image', 'phone_number', 'barangay', 'is_barangay_captain')
    search_fields = ('user__username', 'user__email', 'phone_number')
    list_filter = ('is_barangay_captain', 'barangay')

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


class EvacuationCenterAdmin(admin.ModelAdmin):
    list_display = ('name', 'barangay', 'capacity', 'current_occupancy', 'status', 'manager')
    list_filter = ('status', 'barangay__municipality', 'barangay')
    search_fields = ('name', 'address', 'manager__username', 'barangay__name')
    date_hierarchy = 'date_created'
    readonly_fields = ('date_created', 'last_updated')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If user is not a superuser and is a barangay captain, only show their centers
        if not request.user.is_superuser:
            try:
                profile = request.user.reporterprofile
                if profile.is_barangay_captain and profile.barangay:
                    return qs.filter(barangay=profile.barangay)
            except:
                pass
        return qs


class EvacueeAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'gender', 'family_name', 'evacuation_center', 'date_admitted', 'date_departed')
    list_filter = ('gender', 'evacuation_center', 'date_admitted', 'date_departed', 'head_of_family')
    search_fields = ('name', 'family_name', 'special_needs', 'evacuation_center__name')
    date_hierarchy = 'date_admitted'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # If user is not a superuser and is a barangay captain, only show evacuees in their centers
        if not request.user.is_superuser:
            try:
                profile = request.user.reporterprofile
                if profile.is_barangay_captain and profile.barangay:
                    return qs.filter(evacuation_center__barangay=profile.barangay)
            except:
                pass
        return qs


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
admin.site.register(EvacuationCenter, EvacuationCenterAdmin)
admin.site.register(Evacuee, EvacueeAdmin)
