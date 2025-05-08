import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from disaster_aid.models import (
    Municipality, Barangay, DisasterType, DistributionType,
    Inventory, ReporterProfile, IncidentReport, IncidentDistribution,
    DisasterAlert, EvacuationCenter, Evacuee, UserNotification
)


class Command(BaseCommand):
    help = 'Populates the database with sample data for testing'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete existing data before creating new data',
        )

    def handle(self, *args, **options):
        if options['flush']:
            self.flush_database()
            self.stdout.write(self.style.SUCCESS('Database flushed successfully'))

        self.stdout.write('Starting database population...')

        # Create data in the correct order to maintain relationships
        self.create_municipalities_and_barangays()
        self.create_disaster_types()
        self.create_distribution_types()
        self.create_users_and_profiles()
        self.create_inventory()
        self.create_incident_reports()
        self.create_incident_distributions()
        self.create_disaster_alerts()
        self.create_evacuation_centers()
        self.create_evacuees()

        self.stdout.write(self.style.SUCCESS('Database populated successfully'))

    def flush_database(self):
        """Delete all existing data from the models we're populating"""
        self.stdout.write('Flushing database...')

        # Delete in reverse order of dependencies
        UserNotification.objects.all().delete()
        Evacuee.objects.all().delete()
        EvacuationCenter.objects.all().delete()
        DisasterAlert.objects.all().delete()
        IncidentDistribution.objects.all().delete()
        IncidentReport.objects.all().delete()
        Inventory.objects.all().delete()
        # Don't delete users if they exist
        # ReporterProfile.objects.all().delete()
        # User.objects.filter(is_superuser=False).delete()
        DistributionType.objects.all().delete()
        DisasterType.objects.all().delete()
        # Keep barangays and municipalities if they exist
        # Barangay.objects.all().delete()
        # Municipality.objects.all().delete()

    def create_municipalities_and_barangays(self):
        """Create sample municipalities and barangays"""
        self.stdout.write('Creating municipalities and barangays...')

        # Check if data already exists
        if Municipality.objects.exists() and Barangay.objects.exists():
            self.stdout.write('Municipalities and barangays already exist, skipping...')
            return

        # Create municipalities
        municipalities = [
            {'name': 'Caloocan', 'psgc_code': '137501'},
            {'name': 'Las Piñas', 'psgc_code': '137502'},
            {'name': 'Makati', 'psgc_code': '137503'},
            {'name': 'Malabon', 'psgc_code': '137504'},
            {'name': 'Mandaluyong', 'psgc_code': '137505'},
        ]

        created_municipalities = []
        for muni_data in municipalities:
            muni, created = Municipality.objects.get_or_create(**muni_data)
            created_municipalities.append(muni)
            if created:
                self.stdout.write(f'Created municipality: {muni.name}')

        # Create barangays for each municipality
        barangay_data = {
            'Caloocan': [
                {'name': 'Barangay 1', 'psgc_code': '13750101'},
                {'name': 'Barangay 2', 'psgc_code': '13750102'},
                {'name': 'Barangay 3', 'psgc_code': '13750103'},
            ],
            'Las Piñas': [
                {'name': 'Almanza Uno', 'psgc_code': '13750201'},
                {'name': 'Almanza Dos', 'psgc_code': '13750202'},
                {'name': 'CAA-BF International', 'psgc_code': '13750203'},
            ],
            'Makati': [
                {'name': 'Poblacion', 'psgc_code': '13750301'},
                {'name': 'Bel-Air', 'psgc_code': '13750302'},
                {'name': 'San Lorenzo', 'psgc_code': '13750303'},
            ],
            'Malabon': [
                {'name': 'Acacia', 'psgc_code': '13750401'},
                {'name': 'Baritan', 'psgc_code': '13750402'},
                {'name': 'Catmon', 'psgc_code': '13750403'},
            ],
            'Mandaluyong': [
                {'name': 'Addition Hills', 'psgc_code': '13750501'},
                {'name': 'Barangka Drive', 'psgc_code': '13750502'},
                {'name': 'Hulo', 'psgc_code': '13750503'},
            ],
        }

        for muni in created_municipalities:
            for brgy_data in barangay_data.get(muni.name, []):
                brgy, created = Barangay.objects.get_or_create(
                    municipality=muni,
                    **brgy_data
                )
                if created:
                    self.stdout.write(f'Created barangay: {brgy.name} in {muni.name}')

    def create_disaster_types(self):
        """Create sample disaster types"""
        self.stdout.write('Creating disaster types...')

        disaster_types = [
            'Typhoon',
            'Flood',
            'Earthquake',
            'Fire',
            'Landslide',
            'Volcanic Eruption',
            'Drought',
            'Storm Surge',
        ]

        for name in disaster_types:
            DisasterType.objects.get_or_create(name=name)

        self.stdout.write(f'Created {len(disaster_types)} disaster types')

    def create_distribution_types(self):
        """Create sample distribution types"""
        self.stdout.write('Creating distribution types...')

        distribution_types = [
            'Food Pack',
            'Drinking Water',
            'Hygiene Kit',
            'Blanket',
            'Medicine',
            'Clothing',
            'Shelter Kit',
            'Rice (kg)',
            'Canned Goods',
        ]

        for name in distribution_types:
            DistributionType.objects.get_or_create(name=name)

        self.stdout.write(f'Created {len(distribution_types)} distribution types')

    def create_users_and_profiles(self):
        """Create sample users and their profiles"""
        self.stdout.write('Creating users and profiles...')

        # Create admin user if it doesn't exist
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@example.com',
                'is_staff': True,
                'is_superuser': True,
                'first_name': 'Admin',
                'last_name': 'User',
            }
        )

        if created:
            admin_user.set_password('admin123')
            admin_user.save()
            self.stdout.write(f'Created admin user: {admin_user.username}')

        # Create barangay captain users
        barangays = Barangay.objects.all()

        for i, barangay in enumerate(barangays):
            username = f'captain_{barangay.name.lower().replace(" ", "_")}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': f'Captain',
                    'last_name': f'{barangay.name}',
                }
            )

            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f'Created user: {user.username}')

            # Create or update profile
            profile, created = ReporterProfile.objects.get_or_create(
                user=user,
                defaults={
                    'barangay': barangay,
                    'is_barangay_captain': True,
                }
            )

            if not created:
                profile.barangay = barangay
                profile.is_barangay_captain = True
                profile.save()

            self.stdout.write(f'Created/updated profile for {user.username} as captain of {barangay.name}')

        # Create regular users
        for i in range(5):
            username = f'user{i+1}'
            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    'email': f'{username}@example.com',
                    'first_name': f'User',
                    'last_name': f'{i+1}',
                }
            )

            if created:
                user.set_password('password123')
                user.save()
                self.stdout.write(f'Created user: {user.username}')

            # Assign random barangay
            random_barangay = random.choice(barangays)

            # Create or update profile
            profile, created = ReporterProfile.objects.get_or_create(
                user=user,
                defaults={
                    'barangay': random_barangay,
                    'is_barangay_captain': False,
                }
            )

            if not created:
                profile.barangay = random_barangay
                profile.save()

            self.stdout.write(f'Created/updated profile for {user.username} in {random_barangay.name}')

    def create_inventory(self):
        """Create inventory for all distribution types"""
        self.stdout.write('Creating inventory...')

        distribution_types = DistributionType.objects.all()

        for dist_type in distribution_types:
            quantity = random.randint(100, 1000)
            inventory, created = Inventory.objects.get_or_create(
                item=dist_type,
                defaults={'quantity_available': quantity}
            )

            if not created:
                inventory.quantity_available = quantity
                inventory.save()

            self.stdout.write(f'Created/updated inventory for {dist_type.name}: {quantity} units')

    def create_incident_reports(self):
        """Create sample incident reports"""
        self.stdout.write('Creating incident reports...')

        # Get users, disaster types, and barangays
        users = User.objects.filter(is_staff=False)
        disaster_types = DisasterType.objects.all()
        barangays = Barangay.objects.all()

        if not users.exists():
            self.stdout.write('No users found, skipping incident reports creation')
            return

        # Create 20 incident reports
        for i in range(20):
            reporter = random.choice(users)
            disaster_type = random.choice(disaster_types)
            barangay = random.choice(barangays)

            # Random date in the past 30 days
            days_ago = random.randint(0, 30)
            incident_date = timezone.now() - timedelta(days=days_ago)

            # Random status
            status = random.choice(['pending', 'verified', 'denied'])

            incident = IncidentReport.objects.create(
                reporter=reporter,
                title=f"{disaster_type.name} in {barangay.name}",
                description=f"A {disaster_type.name.lower()} occurred in {barangay.name}. This is a sample incident report.",
                disaster_type=disaster_type,
                barangay=barangay,
                incident_datetime=incident_date,
                status=status,
                needs_resources=random.choice([True, False]),
            )

            if status == 'denied':
                incident.denial_reason = "This is a sample denial reason."
                incident.save()

            self.stdout.write(f'Created incident report: {incident.title} ({status})')

    def create_incident_distributions(self):
        """Create sample incident distributions"""
        self.stdout.write('Creating incident distributions...')

        # Get incidents that need resources
        incidents = IncidentReport.objects.filter(needs_resources=True)
        distribution_types = DistributionType.objects.all()

        if not incidents.exists():
            self.stdout.write('No incidents found that need resources, skipping distributions creation')
            return

        for incident in incidents:
            # Create 1-3 distribution requests per incident
            for _ in range(random.randint(1, 3)):
                dist_type = random.choice(distribution_types)
                quantity = random.randint(10, 50)

                # Random status
                status = random.choice(['pending', 'approved', 'distributed'])

                distribution = IncidentDistribution.objects.create(
                    incident=incident,
                    distribution_type=dist_type,
                    quantity_requested=quantity,
                    status=status,
                )

                if status in ['approved', 'distributed']:
                    approved_qty = random.randint(5, quantity)
                    distribution.quantity_approved = approved_qty

                    if status == 'distributed':
                        if incident.barangay:
                            distribution.recipient_organization = incident.barangay.name
                            distribution.recipient_name = f"Barangay Captain of {incident.barangay.name}"
                        else:
                            distribution.recipient_organization = "Local Community"
                            distribution.recipient_name = "Community Leader"

                        distribution.recipient_contact = "09123456789"
                        distribution.distributed_by = "Relief Operations Team"
                        distribution.distribution_date = timezone.now() - timedelta(days=random.randint(0, 5))
                        distribution.distribution_notes = "This is a sample distribution note."
                        distribution.beneficiary_list = "Family 1, Family 2, Family 3"
                        distribution.is_fulfilled = True

                    distribution.save()

                self.stdout.write(f'Created distribution for {incident.title}: {quantity} {dist_type.name} ({status})')

    def create_disaster_alerts(self):
        """Create sample disaster alerts"""
        self.stdout.write('Creating disaster alerts...')

        # Get admin user
        admin_user = User.objects.filter(is_staff=True).first()

        if not admin_user:
            self.stdout.write('No admin user found, skipping disaster alerts creation')
            return

        # Create 5 alerts with different severities
        severities = ['low', 'medium', 'high', 'critical']

        for i in range(5):
            severity = severities[i % len(severities)]
            days_ago = random.randint(0, 10)

            alert = DisasterAlert.objects.create(
                title=f"Alert {i+1}: {severity.capitalize()} Risk",
                message=f"This is a sample {severity} severity disaster alert. Please take appropriate precautions.",
                severity=severity,
                created_by=admin_user,
                created_at=timezone.now() - timedelta(days=days_ago),
                is_active=random.choice([True, False]),
            )

            self.stdout.write(f'Created disaster alert: {alert.title}')

    def create_evacuation_centers(self):
        """Create sample evacuation centers"""
        self.stdout.write('Creating evacuation centers...')

        # Get barangays and their captains
        barangays = Barangay.objects.all()

        for barangay in barangays:
            # Try to find the barangay captain
            try:
                captain = User.objects.filter(
                    reporterprofile__barangay=barangay,
                    reporterprofile__is_barangay_captain=True
                ).first()
            except:
                captain = None

            # Create 1-2 evacuation centers per barangay
            for i in range(random.randint(1, 2)):
                status = random.choice(['active', 'standby', 'closed'])
                capacity = random.randint(50, 200)

                # For active centers, add some occupants
                current_occupancy = 0
                if status == 'active':
                    current_occupancy = random.randint(0, capacity)

                center = EvacuationCenter.objects.create(
                    name=f"{barangay.name} Evacuation Center {i+1}",
                    barangay=barangay,
                    address=f"Sample Address, {barangay.name}, {barangay.municipality.name}",
                    capacity=capacity,
                    current_occupancy=current_occupancy,
                    status=status,
                    manager=captain,
                    contact_info="09123456789",
                    facilities="Toilets, Kitchen, Medical Area, Sleeping Area",
                    notes="This is a sample evacuation center.",
                )

                self.stdout.write(f'Created evacuation center: {center.name} ({status})')

    def create_evacuees(self):
        """Create sample evacuees for active evacuation centers"""
        self.stdout.write('Creating evacuees...')

        # Get active evacuation centers
        centers = EvacuationCenter.objects.filter(status='active')

        if not centers.exists():
            self.stdout.write('No active evacuation centers found, skipping evacuees creation')
            return

        for center in centers:
            # Reset occupancy to recalculate based on actual evacuees
            center.current_occupancy = 0
            center.save()

            # Create 5-10 families
            num_families = random.randint(5, 10)

            for f in range(num_families):
                family_name = f"Family {f+1}"

                # Create 2-6 members per family
                num_members = random.randint(2, 6)

                for m in range(num_members):
                    # First member is head of family
                    is_head = (m == 0)

                    # Random age based on role
                    if is_head:
                        age = random.randint(25, 65)
                        gender = random.choice(['male', 'female'])
                    else:
                        # Children or other family members
                        age = random.randint(1, 70)
                        gender = random.choice(['male', 'female', 'other'])

                    # Some evacuees have special needs
                    special_needs = None
                    if random.random() < 0.2:  # 20% chance
                        needs = [
                            "Requires wheelchair access",
                            "Diabetes - needs regular medication",
                            "Asthma - has inhaler",
                            "Pregnant - 7 months",
                            "Elderly - needs assistance with mobility",
                            "Infant - requires formula",
                        ]
                        special_needs = random.choice(needs)

                    # Some evacuees have already departed
                    date_departed = None
                    if random.random() < 0.3:  # 30% chance
                        days_ago = random.randint(1, 5)
                        date_departed = timezone.now() - timedelta(days=days_ago)

                    evacuee = Evacuee.objects.create(
                        evacuation_center=center,
                        name=f"{family_name} Member {m+1}",
                        age=age,
                        gender=gender,
                        head_of_family=is_head,
                        family_name=family_name,
                        special_needs=special_needs,
                        date_departed=date_departed,
                        contact_number="09123456789" if is_head else None,
                    )

                    # Update center occupancy for active evacuees
                    if not date_departed:
                        center.current_occupancy += 1

                    self.stdout.write(f'Created evacuee: {evacuee.name} in {center.name}')

            # Save the updated occupancy
            center.save()
            self.stdout.write(f'Updated occupancy for {center.name}: {center.current_occupancy}')
