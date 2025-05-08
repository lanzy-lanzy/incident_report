from django.core.management.base import BaseCommand
from disaster_aid.models import Municipality, Barangay

class Command(BaseCommand):
    help = 'Populates the database with Tambulig municipality and its barangays using PSGC codes'

    def handle(self, *args, **options):
        # Create Tambulig Municipality
        # PSGC Code for Tambulig, Zamboanga del Sur: 097322000
        tambulig, created = Municipality.objects.get_or_create(
            name='Tambulig',
            psgc_code='097322000'
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS(f'Created Municipality: {tambulig.name}'))
        else:
            self.stdout.write(f'Municipality already exists: {tambulig.name}')
        
        # List of barangays in Tambulig with their PSGC codes
        # Source: Philippine Statistics Authority (PSA) PSGC
        barangays = [
            {'name': 'Bagong Baroy', 'psgc_code': '097322001'},
            {'name': 'Bagong Kauswagan', 'psgc_code': '097322002'},
            {'name': 'Bagong Tabogon', 'psgc_code': '097322003'},
            {'name': 'Calolot', 'psgc_code': '097322004'},
            {'name': 'Dalaon', 'psgc_code': '097322005'},
            {'name': 'Fabian', 'psgc_code': '097322006'},
            {'name': 'Kapalaran', 'psgc_code': '097322007'},
            {'name': 'Libato', 'psgc_code': '097322008'},
            {'name': 'Lower Liasan', 'psgc_code': '097322009'},
            {'name': 'Lower Lodiong', 'psgc_code': '097322010'},
            {'name': 'Lower Tiparak', 'psgc_code': '097322011'},
            {'name': 'Pelocuban', 'psgc_code': '097322012'},
            {'name': 'Poblacion', 'psgc_code': '097322013'},
            {'name': 'Riverside', 'psgc_code': '097322014'},
            {'name': 'Sagrada Familia', 'psgc_code': '097322015'},
            {'name': 'San Jose', 'psgc_code': '097322016'},
            {'name': 'San Vicente', 'psgc_code': '097322017'},
            {'name': 'Sumalig', 'psgc_code': '097322018'},
            {'name': 'Unidos', 'psgc_code': '097322019'},
            {'name': 'Upper Liaison', 'psgc_code': '097322020'},
            {'name': 'Upper Lodiong', 'psgc_code': '097322021'},
            {'name': 'Upper Tiparak', 'psgc_code': '097322022'},
        ]
        
        # Create barangays
        created_count = 0
        existing_count = 0
        
        for barangay_data in barangays:
            barangay, created = Barangay.objects.get_or_create(
                name=barangay_data['name'],
                psgc_code=barangay_data['psgc_code'],
                municipality=tambulig
            )
            
            if created:
                created_count += 1
                self.stdout.write(f'Created Barangay: {barangay.name}')
            else:
                existing_count += 1
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully populated Tambulig with {created_count} new barangays. '
            f'{existing_count} barangays already existed.'
        ))
