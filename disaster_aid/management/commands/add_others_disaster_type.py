from django.core.management.base import BaseCommand
from disaster_aid.models import DisasterType

class Command(BaseCommand):
    help = 'Adds the "Others" disaster type to the database'

    def handle(self, *args, **kwargs):
        self.stdout.write('Checking for "Others" disaster type...')
        
        # Check if "Others" already exists
        if not DisasterType.objects.filter(name='Others').exists():
            DisasterType.objects.create(name='Others')
            self.stdout.write(self.style.SUCCESS('Successfully added "Others" disaster type!'))
        else:
            self.stdout.write(self.style.SUCCESS('"Others" disaster type already exists.'))
