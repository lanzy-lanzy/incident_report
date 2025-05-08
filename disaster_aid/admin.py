from django.contrib import admin
from .models import (
    DisasterType,
    DistributionType,
    Inventory,
    ReporterProfile,
    IncidentReport,
    IncidentDistribution
)

class ReporterProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'profile_image')
    search_fields = ('user__username', 'user__email')

class IncidentReportAdmin(admin.ModelAdmin):
    list_display = ('title', 'location', 'disaster_type', 'reporter', 'date_reported', 'is_verified')
    list_filter = ('disaster_type', 'is_verified', 'date_reported')
    search_fields = ('title', 'description', 'location', 'reporter__username')
    date_hierarchy = 'date_reported'

class IncidentDistributionAdmin(admin.ModelAdmin):
    list_display = ('incident', 'distribution_type', 'quantity_requested', 'quantity_approved', 'is_fulfilled')
    list_filter = ('is_fulfilled', 'distribution_type')
    search_fields = ('incident__title', 'distribution_type__name')

class InventoryAdmin(admin.ModelAdmin):
    list_display = ('item', 'quantity_available')
    search_fields = ('item__name',)

# Register models
admin.site.register(DisasterType)
admin.site.register(DistributionType)
admin.site.register(Inventory, InventoryAdmin)
admin.site.register(ReporterProfile, ReporterProfileAdmin)
admin.site.register(IncidentReport, IncidentReportAdmin)
admin.site.register(IncidentDistribution, IncidentDistributionAdmin)
