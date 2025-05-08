from django.db import models
from django.contrib.auth.models import User


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


# Reporter profile with only profile image
class ReporterProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_image = models.ImageField(upload_to='profile_images/', null=True, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"


# Reported incidents
class IncidentReport(models.Model):
    reporter = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    disaster_type = models.ForeignKey(DisasterType, on_delete=models.SET_NULL, null=True)
    location = models.CharField(max_length=255)
    date_reported = models.DateTimeField(auto_now_add=True)
    is_verified = models.BooleanField(default=False)
    needs_resources = models.BooleanField(default=False)
    photo_1 = models.ImageField(upload_to='incident_photos/', null=True, blank=True)
    photo_2 = models.ImageField(upload_to='incident_photos/', null=True, blank=True)
    photo_3 = models.ImageField(upload_to='incident_photos/', null=True, blank=True)

    def __str__(self):
        return f"{self.title} - {self.location}"

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


# Distributions linked to incidents, based on inventory
class IncidentDistribution(models.Model):
    incident = models.ForeignKey(IncidentReport, on_delete=models.CASCADE)
    distribution_type = models.ForeignKey(DistributionType, on_delete=models.CASCADE)
    quantity_requested = models.PositiveIntegerField()
    quantity_approved = models.PositiveIntegerField(default=0)
    is_fulfilled = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.distribution_type.name} for {self.incident.title}"

    def approve_distribution(self, quantity):
        """
        Approves a distribution based on available inventory.
        Deducts quantity from inventory if stock is sufficient.
        """
        inventory = Inventory.objects.get(item=self.distribution_type)
        if quantity <= inventory.quantity_available:
            self.quantity_approved = quantity
            inventory.quantity_available -= quantity
            inventory.save()
            self.is_fulfilled = True
            self.save()
        else:
            raise ValueError("Not enough stock in inventory.")
