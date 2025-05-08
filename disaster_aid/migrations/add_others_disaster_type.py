from django.db import migrations

def add_others_disaster_type(apps, schema_editor):
    DisasterType = apps.get_model('disaster_aid', 'DisasterType')
    
    # Check if "Others" already exists
    if not DisasterType.objects.filter(name='Others').exists():
        DisasterType.objects.create(name='Others')

def remove_others_disaster_type(apps, schema_editor):
    DisasterType = apps.get_model('disaster_aid', 'DisasterType')
    DisasterType.objects.filter(name='Others').delete()

class Migration(migrations.Migration):

    dependencies = [
        ('disaster_aid', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(add_others_disaster_type, remove_others_disaster_type),
    ]
