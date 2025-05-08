from django.core.management.base import BaseCommand
from disaster_aid.models import DisasterType, DistributionType, Inventory

class Command(BaseCommand):
    help = 'Sets up initial data for the disaster aid system'

    def handle(self, *args, **kwargs):
        self.stdout.write('Setting up initial data...')
        
        # Create disaster types
        disaster_types = [
            'Earthquake',
            'Flood',
            'Hurricane',
            'Wildfire',
            'Tornado',
            'Drought',
            'Landslide',
            'Tsunami',
            'Volcanic Eruption',
            'Winter Storm'
        ]
        
        for disaster_type in disaster_types:
            DisasterType.objects.get_or_create(name=disaster_type)
            self.stdout.write(f'Created disaster type: {disaster_type}')
        
        # Create distribution types and inventory
        distribution_types = [
            'Food',
            'Water',
            'Medical Supplies',
            'Clothing',
            'Shelter',
            'Blankets',
            'Hygiene Kits',
            'Baby Supplies',
            'Tools',
            'Generators'
        ]
        
        for distribution_type in distribution_types:
            dist_type, created = DistributionType.objects.get_or_create(name=distribution_type)
            
            # Create inventory for this distribution type with initial quantity
            Inventory.objects.get_or_create(
                item=dist_type,
                defaults={'quantity_available': 100}
            )
            
            self.stdout.write(f'Created distribution type and inventory: {distribution_type}')
        
        self.stdout.write(self.style.SUCCESS('Successfully set up initial data!'))
