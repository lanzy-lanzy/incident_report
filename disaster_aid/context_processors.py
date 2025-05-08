from .models import IncidentReport

def incident_notifications(request):
    """
    Context processor to provide incident notifications to all templates.
    """
    context = {
        'unverified_incidents_count': 0,
        'recent_unverified_incidents': [],
        'has_notifications': False,
    }
    
    # Only provide notifications for staff users
    if request.user.is_authenticated and request.user.is_staff:
        # Get count of unverified incidents
        unverified_incidents_count = IncidentReport.objects.filter(is_verified=False).count()
        
        # Get 5 most recent unverified incidents
        recent_unverified_incidents = IncidentReport.objects.filter(
            is_verified=False
        ).order_by('-date_reported')[:5]
        
        context.update({
            'unverified_incidents_count': unverified_incidents_count,
            'recent_unverified_incidents': recent_unverified_incidents,
            'has_notifications': unverified_incidents_count > 0,
        })
    
    return context
