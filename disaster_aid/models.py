from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


# Location models for PSGC-based locations
class Municipality(models.Model):
    name = models.CharField(max_length=100)
    psgc_code = models.CharField(max_length=20, unique=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name_plural = "Municipalities"


class Barangay(models.Model):
    name = models.CharField(max_length=100)
    psgc_code = models.CharField(max_length=20, unique=True)
    municipality = models.ForeignKey(Municipality, on_delete=models.CASCADE, related_name='barangays')

    def __str__(self):
        return f"{self.name}, {self.municipality.name}"

    class Meta:
        verbose_name_plural = "Barangays"
        ordering = ['name']


# Types of disasters (e.g., Earthquake, Flood)
class DisasterType(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# Types of distributable items (e.g., Food, Water)
class DistributionType(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# Inventory of available items
class Inventory(models.Model):
    item = models.OneToOneField(DistributionType, on_delete=models.CASCADE)
    quantity_available = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.item.name} - {self.quantity_available} in stock"


# Reporter profile with profile image and barangay
class ReporterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)
    barangay = models.ForeignKey(Barangay, on_delete=models.SET_NULL, null=True, blank=True)
    is_barangay_captain = models.BooleanField(default=False, help_text="Designates whether this user is a barangay captain")

    def __str__(self):
        if self.barangay:
            return f"{self.user.username}'s Profile - {self.barangay.name}"
        return f"{self.user.username}'s Profile"


# Reported incidents
class IncidentReport(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('verified', 'Verified'),
        ('denied', 'Denied'),
    )

    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    disaster_type = models.ForeignKey(DisasterType, on_delete=models.SET_NULL, null=True)
    other_disaster_type = models.CharField(max_length=100, blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)  # Keeping for backward compatibility
    barangay = models.ForeignKey(Barangay, on_delete=models.SET_NULL, null=True, blank=True, related_name='incidents')
    incident_datetime = models.DateTimeField(null=True, blank=True, help_text="When the incident actually occurred")
    date_reported = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    is_verified = models.BooleanField(default=False)  # Keeping for backward compatibility
    denial_reason = models.TextField(null=True, blank=True)
    needs_resources = models.BooleanField(default=False)
    photo_1 = models.ImageField(upload_to='incident_photos/', null=True, blank=True)
    photo_2 = models.ImageField(upload_to='incident_photos/', null=True, blank=True)
    photo_3 = models.ImageField(upload_to='incident_photos/', null=True, blank=True)

    def __str__(self):
        location_str = self.barangay if self.barangay else self.location
        return f"{self.title} - {location_str}"

    @property
    def has_photos(self):
        """Check if the incident has any photos uploaded"""
        return bool(self.photo_1 or self.photo_2 or self.photo_3)

    def get_photos(self):
        """Return a list of all uploaded photos"""
        photos = []
        if self.photo_1:
            photos.append(self.photo_1)
        if self.photo_2:
            photos.append(self.photo_2)
        if self.photo_3:
            photos.append(self.photo_3)
        return photos

    def save(self, *args, **kwargs):
        """Override save to maintain backward compatibility with is_verified field"""
        if self.status == 'verified' and not self.is_verified:
            self.is_verified = True
        elif self.status != 'verified' and self.is_verified:
            self.is_verified = False
        super().save(*args, **kwargs)

    def verify(self):
        """Mark the incident as verified"""
        self.status = 'verified'
        self.is_verified = True
        self.save()

    def deny(self, reason):
        """Mark the incident as denied with a reason"""
        self.status = 'denied'
        self.is_verified = False
        self.denial_reason = reason
        self.save()


# Distributions linked to incidents, based on inventory
class IncidentDistribution(models.Model):
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('distributed', 'Distributed'),
    )

    incident = models.ForeignKey(IncidentReport, on_delete=models.CASCADE)
    distribution_type = models.ForeignKey(DistributionType, on_delete=models.CASCADE)
    quantity_requested = models.PositiveIntegerField()
    quantity_approved = models.PositiveIntegerField(default=0)
    is_fulfilled = models.BooleanField(default=False)  # Keeping for backward compatibility
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    # Distribution details
    recipient_organization = models.CharField(max_length=255, blank=True, null=True)  # e.g., Barangay name
    recipient_name = models.CharField(max_length=255, blank=True, null=True)  # e.g., Barangay Captain
    recipient_contact = models.CharField(max_length=255, blank=True, null=True)
    distributed_by = models.CharField(max_length=255, blank=True, null=True)
    distribution_date = models.DateTimeField(blank=True, null=True)
    distribution_notes = models.TextField(blank=True, null=True)
    beneficiary_list = models.TextField(blank=True, null=True)  # List of affected families/constituents

    def __str__(self):
        return f"{self.distribution_type.name} for {self.incident.title}"

    def approve_distribution(self, quantity):
        """
        Approves a distribution request without deducting from inventory.
        Only marks the request as approved and sets the approved quantity.
        """
        inventory = Inventory.objects.get(item=self.distribution_type)
        if quantity <= inventory.quantity_available:
            self.quantity_approved = quantity
            self.status = 'approved'
            self.save()

            # Create notification for the incident reporter
            from .models import UserNotification
            UserNotification.objects.create(
                user=self.incident.reporter,
                notification_type='resource_approved',
                title='Resource Request Approved',
                message=f'Your request for {quantity} {self.distribution_type.name} has been approved and is pending distribution.',
                incident=self.incident
            )

    def complete_distribution(self, distribution_data):
        """
        Completes the distribution process by deducting from inventory
        and marking the distribution as fulfilled.

        Args:
            distribution_data: Dictionary containing distribution details
                - recipient_organization: Organization receiving the resources
                - recipient_name: Name of the person receiving the resources
                - recipient_contact: Contact information of the recipient
                - distributed_by: Name of the person distributing the resources
                - distribution_notes: Additional notes about the distribution
        """
        from django.utils import timezone

        inventory = Inventory.objects.get(item=self.distribution_type)
        if self.quantity_approved <= inventory.quantity_available:
            inventory.quantity_available -= self.quantity_approved
            inventory.save()

            # Update distribution details
            self.recipient_organization = distribution_data.get('recipient_organization', '')
            self.recipient_name = distribution_data.get('recipient_name', '')
            self.recipient_contact = distribution_data.get('recipient_contact', '')
            self.distributed_by = distribution_data.get('distributed_by', '')
            self.distribution_notes = distribution_data.get('distribution_notes', '')
            self.beneficiary_list = distribution_data.get('beneficiary_list', '')
            self.distribution_date = timezone.now()
            self.status = 'distributed'
            self.is_fulfilled = True
            self.save()

            # Create notification for the incident reporter
            from .models import UserNotification
            recipient_info = f"{self.recipient_name}"
            if self.recipient_organization:
                recipient_info = f"{self.recipient_name} from {self.recipient_organization}"

            UserNotification.objects.create(
                user=self.incident.reporter,
                notification_type='resource_fulfilled',
                title='Resources Distributed',
                message=f'Your approved request for {self.quantity_approved} {self.distribution_type.name} has been distributed to {recipient_info}.',
                incident=self.incident
            )
        else:
            raise ValueError(f"Not enough {self.distribution_type.name} in stock. Available: {inventory.quantity_available}, Requested: {self.quantity_approved}")


# Disaster Alert for upcoming disasters
class DisasterAlert(models.Model):
    SEVERITY_CHOICES = (
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    )

    title = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(max_length=20, choices=SEVERITY_CHOICES, default='medium')
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_alerts')
    created_at = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title} ({self.get_severity_display()})"

    def deactivate(self):
        """Deactivate the alert"""
        self.is_active = False
        self.save()


# Evacuation Centers
class EvacuationCenter(models.Model):
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('standby', 'Standby'),
        ('closed', 'Closed'),
    )

    name = models.CharField(max_length=255)
    barangay = models.ForeignKey(Barangay, on_delete=models.CASCADE, related_name='evacuation_centers')
    address = models.TextField(help_text="Detailed address of the evacuation center")
    capacity = models.PositiveIntegerField(help_text="Maximum number of people the center can accommodate")
    current_occupancy = models.PositiveIntegerField(default=0, help_text="Current number of people in the center")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='standby')
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,
                               help_text="Barangay captain or designated manager of this evacuation center")
    contact_info = models.CharField(max_length=255, blank=True, null=True,
                                   help_text="Contact information for the evacuation center")
    facilities = models.TextField(blank=True, null=True,
                                 help_text="Available facilities (e.g., toilets, kitchen, medical area)")
    date_created = models.DateTimeField(auto_now_add=True)
    last_updated = models.DateTimeField(auto_now=True)
    notes = models.TextField(blank=True, null=True, help_text="Additional notes about the evacuation center")

    def __str__(self):
        return f"{self.name} - {self.barangay.name}"

    def update_occupancy(self, count):
        """Update the current occupancy of the evacuation center"""
        if count > self.capacity:
            raise ValueError(f"Occupancy cannot exceed capacity ({self.capacity})")
        self.current_occupancy = count
        self.save()

    def activate(self):
        """Activate the evacuation center"""
        self.status = 'active'
        self.save()

    def deactivate(self):
        """Set the evacuation center to standby mode"""
        self.status = 'standby'
        self.save()

    def close(self):
        """Close the evacuation center"""
        self.status = 'closed'
        self.current_occupancy = 0
        self.save()


# Evacuees in evacuation centers
class Evacuee(models.Model):
    evacuation_center = models.ForeignKey(EvacuationCenter, on_delete=models.CASCADE, related_name='evacuees')
    name = models.CharField(max_length=255)
    age = models.PositiveIntegerField()
    gender = models.CharField(max_length=10, choices=[('male', 'Male'), ('female', 'Female'), ('other', 'Other')])
    head_of_family = models.BooleanField(default=False)
    family_name = models.CharField(max_length=255, blank=True, null=True,
                                  help_text="Family name for grouping related evacuees")
    special_needs = models.TextField(blank=True, null=True,
                                    help_text="Any special needs or medical conditions")
    date_admitted = models.DateTimeField(auto_now_add=True)
    date_departed = models.DateTimeField(null=True, blank=True)
    contact_number = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self):
        return f"{self.name} - {self.evacuation_center.name}"

    def depart(self):
        """Record the departure of an evacuee"""
        self.date_departed = timezone.now()
        self.save()

        # Update the evacuation center occupancy
        center = self.evacuation_center
        center.current_occupancy = max(0, center.current_occupancy - 1)
        center.save()


# User notifications
class UserNotification(models.Model):
    NOTIFICATION_TYPES = (
        ('incident_verified', 'Incident Verified'),
        ('incident_denied', 'Incident Denied'),
        ('resource_approved', 'Resource Request Approved'),
        ('resource_fulfilled', 'Resource Request Fulfilled'),
        ('evacuation_activated', 'Evacuation Center Activated'),
        ('evacuation_update', 'Evacuation Center Update'),
    )

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    incident = models.ForeignKey(IncidentReport, on_delete=models.CASCADE, null=True, blank=True)
    evacuation_center = models.ForeignKey(EvacuationCenter, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.notification_type} for {self.user.username}"

    def mark_as_read(self):
        """Mark the notification as read"""
        self.is_read = True
        self.save()
