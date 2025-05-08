from .models import IncidentReport, UserNotification

def incident_notifications(request):
    """
    Context processor to provide incident notifications to all templates.
    """
    context = {
        'unverified_incidents_count': 0,
        'recent_unverified_incidents': [],
        'has_admin_notifications': False,
        'user_notifications': [],
        'unread_user_notifications_count': 0,
        'has_user_notifications': False,
    }

    if request.user.is_authenticated:
        # Admin notifications for staff users
        if request.user.is_staff:
            # Get count of unverified incidents
            unverified_incidents_count = IncidentReport.objects.filter(is_verified=False).count()

            # Get 5 most recent unverified incidents
            recent_unverified_incidents = IncidentReport.objects.filter(
                is_verified=False
            ).order_by('-date_reported')[:5]

            context.update({
                'unverified_incidents_count': unverified_incidents_count,
                'recent_unverified_incidents': recent_unverified_incidents,
                'has_admin_notifications': unverified_incidents_count > 0,
            })

        # User notifications for all authenticated users
        user_notifications = UserNotification.objects.filter(user=request.user).order_by('-created_at')[:5]
        unread_count = UserNotification.objects.filter(user=request.user, is_read=False).count()

        context.update({
            'user_notifications': user_notifications,
            'unread_user_notifications_count': unread_count,
            'has_user_notifications': unread_count > 0,
        })

    return context
