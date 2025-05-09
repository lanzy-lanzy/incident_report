from django.core.management.base import BaseCommand
from disaster_aid.models import Municipality, Barangay
from django.db import transaction

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

        # First, clear existing barangays for Tambulig to avoid conflicts
        with transaction.atomic():
            # Delete existing barangays for this municipality to avoid conflicts
            existing_barangays = Barangay.objects.filter(municipality=tambulig)
            if existing_barangays.exists():
                self.stdout.write(f'Removing {existing_barangays.count()} existing barangays for {tambulig.name}')
                existing_barangays.delete()

            # List of barangays in Tambulig with their PSGC codes
            # Source: Updated list of barangays
            barangays = [
                {'name': 'Alang-alang', 'psgc_code': '097322001'},
                {'name': 'Angeles', 'psgc_code': '097322002'},
                {'name': 'Bag-ong Kauswagan', 'psgc_code': '097322003'},
                {'name': 'Bag-ong Tabogon', 'psgc_code': '097322004'},
                {'name': 'Balugo', 'psgc_code': '097322005'},
                {'name': 'Cabgan', 'psgc_code': '097322006'},
                {'name': 'Calolot', 'psgc_code': '097322007'},
                {'name': 'Dimalinao', 'psgc_code': '097322008'},
                {'name': 'Fabian (Balucot)', 'psgc_code': '097322009'},
                {'name': 'Gabunon', 'psgc_code': '097322010'},
                {'name': 'Happy Valley (Poblacion)', 'psgc_code': '097322011'},
                {'name': 'Kapalaran', 'psgc_code': '097322012'},
                {'name': 'Libato', 'psgc_code': '097322013'},
                {'name': 'Limamaan', 'psgc_code': '097322014'},
                {'name': 'Lower Liasan', 'psgc_code': '097322015'},
                {'name': 'Lower Lodiong (Poblacion)', 'psgc_code': '097322016'},
                {'name': 'Lower Tiparak', 'psgc_code': '097322017'},
                {'name': 'Lower Usogan', 'psgc_code': '097322018'},
                {'name': 'Maya-maya', 'psgc_code': '097322019'},
                {'name': 'New Village (Poblacion)', 'psgc_code': '097322020'},
                {'name': 'Pelocuban', 'psgc_code': '097322021'},
                {'name': 'Riverside (Poblacion)', 'psgc_code': '097322022'},
                {'name': 'Sagrada Familia', 'psgc_code': '097322023'},
                {'name': 'San Jose', 'psgc_code': '097322024'},
                {'name': 'San Vicente', 'psgc_code': '097322025'},
                {'name': 'Sumalig', 'psgc_code': '097322026'},
                {'name': 'Tuluan', 'psgc_code': '097322027'},
                {'name': 'Tungawan', 'psgc_code': '097322028'},
                {'name': 'Upper Liaison', 'psgc_code': '097322029'},
                {'name': 'Upper Lodiong', 'psgc_code': '097322030'},
                {'name': 'Upper Tiparak', 'psgc_code': '097322031'},
            ]

            # Create barangays
            created_count = 0

            for barangay_data in barangays:
                barangay = Barangay.objects.create(
                    name=barangay_data['name'],
                    psgc_code=barangay_data['psgc_code'],
                    municipality=tambulig
                )
                created_count += 1
                self.stdout.write(f'Created Barangay: {barangay.name}')

            self.stdout.write(self.style.SUCCESS(
                f'Successfully populated Tambulig with {created_count} new barangays.'
            ))
