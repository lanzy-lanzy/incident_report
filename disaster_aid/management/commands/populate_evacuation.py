import random
from datetime import timedelta
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from django.db import transaction
from disaster_aid.models import (
    Barangay, EvacuationCenter, Evacuee, UserNotification
)


class Command(BaseCommand):
    help = 'Populates the database with sample evacuation centers and evacuees'

    def add_arguments(self, parser):
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Delete existing evacuation data before creating new data',
        )

    def handle(self, *args, **options):
        if options['flush']:
            self.flush_database()
            self.stdout.write(self.style.SUCCESS('Evacuation data flushed successfully'))

        self.stdout.write('Starting evacuation data population...')
        
        # Create evacuation centers and evacuees
        self.create_evacuation_centers()
        self.create_evacuees()
        
        self.stdout.write(self.style.SUCCESS('Evacuation data populated successfully'))

    def flush_database(self):
        """Delete all existing evacuation data"""
        self.stdout.write('Flushing evacuation data...')
        
        # Delete in reverse order of dependencies
        Evacuee.objects.all().delete()
        EvacuationCenter.objects.all().delete()

    def create_evacuation_centers(self):
        """Create sample evacuation centers"""
        self.stdout.write('Creating evacuation centers...')
        
        # Get barangays and their captains
        barangays = Barangay.objects.all()
        
        if not barangays.exists():
            self.stdout.write('No barangays found, skipping evacuation centers creation')
            return
        
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
