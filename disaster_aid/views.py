from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.db.models import Count
from django.http import HttpResponse, JsonResponse
from django.core.paginator import Paginator
from django.utils import timezone
from .forms import (
    LoginForm, RegisterForm, IncidentReportForm,
    DistributionRequestForm, InventoryForm, DenyIncidentForm,
    DisasterAlertForm, EvacuationCenterForm, EvacueeForm
)
from .models import (
    IncidentReport, DisasterType, DistributionType,
    Inventory, IncidentDistribution, UserNotification,
    DisasterAlert, Barangay, Municipality,
    EvacuationCenter, Evacuee
)
import io
import os
from datetime import datetime

def home(request):
    # Redirect admin users to the admin dashboard if they're logged in
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_dashboard')

    # Get recent incidents for the homepage
    recent_incidents = IncidentReport.objects.filter(is_verified=True).order_by('-date_reported')[:3]
    disaster_types = DisasterType.objects.all()

    context = {
        'recent_incidents': recent_incidents,
        'disaster_types': disaster_types,
    }
    return render(request, 'home.html', context)

def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Welcome back, {username}!")
                return redirect('home')
            else:
                messages.error(request, "Invalid username or password.")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = LoginForm()

    return render(request, 'auth/login.html', {'form': form})

def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')

    if request.method == 'POST':
        # Debug: Print POST data (excluding sensitive info)
        debug_data = {k: v for k, v in request.POST.items() if k not in ['password1', 'password2']}
        print(f"DEBUG - POST data: {debug_data}")
        print(f"DEBUG - FILES data: {request.FILES}")

        form = RegisterForm(request.POST, request.FILES)

        # Debug: Check if form is bound correctly
        print(f"DEBUG - Form is bound: {form.is_bound}")

        if form.is_valid():
            print("DEBUG - Form is valid")
            # Debug: Print cleaned data (excluding sensitive info)
            debug_cleaned = {k: v for k, v in form.cleaned_data.items() if k not in ['password1', 'password2']}
            print(f"DEBUG - Cleaned data: {debug_cleaned}")

            try:
                user = form.save()
                print(f"DEBUG - User created: {user.username}, {user.email}")
                login(request, user)
                messages.success(request, f"Account created for {user.username}!")
                return redirect('home')
            except Exception as e:
                import traceback
                print(f"DEBUG - Exception during save: {str(e)}")
                print(traceback.format_exc())
                messages.error(request, f"Error creating account: {str(e)}")
        else:
            print("DEBUG - Form is invalid")
            print(f"DEBUG - Form errors: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RegisterForm()
        print("DEBUG - New form created for GET request")

    return render(request, 'auth/register.html', {'form': form})

def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out.")
    return redirect('home')

# Incident Reporting Views
@login_required
def report_incident(request):
    # Prevent admin users from reporting incidents
    if request.user.is_staff:
        messages.error(request, "Admin users cannot report incidents. Please use a regular user account.")
        return redirect('admin_dashboard')

    # Get available resource types for the form
    resource_types = DistributionType.objects.filter(inventory__quantity_available__gt=0)

    # Print out all disaster types for debugging
    disaster_types = DisasterType.objects.all()
    print("Available disaster types:")
    for dt in disaster_types:
        print(f"- {dt.id}: {dt.name}")

    if request.method == 'POST':
        form = IncidentReportForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the incident report
            incident = form.save(commit=False)
            incident.reporter = request.user

            # Handle "Others" disaster type
            if incident.disaster_type and incident.disaster_type.name == 'Others':
                # Keep the disaster_type as "Others" but also store the specific type
                incident.other_disaster_type = form.cleaned_data.get('other_disaster_type', '')

            incident.save()

            # Check if photos were uploaded
            has_photos = False
            if form.cleaned_data.get('photo_1') or form.cleaned_data.get('photo_2') or form.cleaned_data.get('photo_3'):
                has_photos = True

            # Process resource requests if needed
            if form.cleaned_data.get('needs_resources'):
                # Get all resource requests from the form
                resource_count = 1
                has_resources = False

                while True:
                    resource_type_id = request.POST.get(f'resource_type_{resource_count}')
                    quantity = request.POST.get(f'quantity_{resource_count}')
                    other_resource_type = request.POST.get(f'other_resource_type_{resource_count}')

                    if not resource_type_id or not quantity:
                        # No more resources to process
                        if resource_count == 1:
                            # No resources were specified
                            messages.warning(request, "You indicated resource needs but didn't specify any resources.")
                        break

                    try:
                        quantity = int(quantity)
                        if quantity <= 0:
                            messages.warning(request, "Quantity must be greater than 0.")
                            continue

                        # Handle "Others" resource type
                        if resource_type_id == 'others':
                            if not other_resource_type:
                                messages.warning(request, "Please specify the other resource type.")
                                continue

                            # Create a new distribution request with notes
                            distribution = IncidentDistribution.objects.create(
                                incident=incident,
                                distribution_type=None,  # No specific distribution type
                                quantity_requested=quantity,
                                distribution_notes=f"Other resource type: {other_resource_type}"
                            )
                            has_resources = True
                            messages.info(request, f"Your request for '{other_resource_type}' has been recorded and will be reviewed.")
                        else:
                            # Regular resource type
                            resource_type = DistributionType.objects.get(id=resource_type_id)

                            # Check if there's enough inventory
                            inventory = Inventory.objects.get(item=resource_type)
                            if inventory.quantity_available >= quantity:
                                # Create the distribution request
                                IncidentDistribution.objects.create(
                                    incident=incident,
                                    distribution_type=resource_type,
                                    quantity_requested=quantity
                                )
                                has_resources = True
                            else:
                                messages.warning(request, f"Not enough {resource_type.name} in inventory. Available: {inventory.quantity_available}")
                    except (DistributionType.DoesNotExist, Inventory.DoesNotExist, ValueError):
                        messages.warning(request, f"Invalid resource request at position {resource_count}.")

                    resource_count += 1

                # Customize success message based on what was included
                if has_resources and has_photos:
                    messages.success(request, "Incident reported with resource requests and photos. It will be reviewed by our team.")
                elif has_resources:
                    messages.success(request, "Incident reported with resource requests. It will be reviewed by our team.")
                elif has_photos:
                    messages.success(request, "Incident reported with photos. It will be reviewed by our team.")
                else:
                    messages.success(request, "Incident reported successfully. It will be reviewed by our team.")
            else:
                if has_photos:
                    messages.success(request, "Incident reported with photos. It will be reviewed by our team.")
                else:
                    messages.success(request, "Incident reported successfully. It will be reviewed by our team.")

            return redirect('dashboard')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = IncidentReportForm()

    context = {
        'form': form,
        'resource_types': resource_types,
    }
    return render(request, 'incidents/report_incident.html', context)

# Dashboard Views
@login_required
def dashboard(request):
    # Redirect admin users to the admin dashboard
    if request.user.is_staff:
        return redirect('admin_dashboard')

    # Get user's reported incidents
    user_incidents = IncidentReport.objects.filter(reporter=request.user).order_by('-date_reported')

    # Get statistics
    incident_count = IncidentReport.objects.count()
    verified_count = IncidentReport.objects.filter(is_verified=True).count()
    pending_count = incident_count - verified_count

    # Get distribution statistics
    distribution_count = IncidentDistribution.objects.count()
    fulfilled_count = IncidentDistribution.objects.filter(is_fulfilled=True).count()

    # Paginate user incidents
    paginator = Paginator(user_incidents, 10)  # Show 10 incidents per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'incident_count': incident_count,
        'verified_count': verified_count,
        'pending_count': pending_count,
        'distribution_count': distribution_count,
        'fulfilled_count': fulfilled_count,
    }

    return render(request, 'dashboard/dashboard.html', context)

@login_required
def incident_detail(request, incident_id):
    incident = get_object_or_404(IncidentReport, id=incident_id)

    # Check if user is authorized to view this incident
    if not request.user.is_staff and incident.reporter != request.user:
        messages.error(request, "You are not authorized to view this incident.")
        return redirect('dashboard')

    # Get distributions for this incident
    distributions = IncidentDistribution.objects.filter(incident=incident)

    # Get inventory information for each distribution type
    inventories = {inv.item_id: inv.quantity_available for inv in Inventory.objects.all()}

    # Handle distribution request form
    if request.method == 'POST':
        form = DistributionRequestForm(request.POST)
        if form.is_valid():
            distribution = form.save(commit=False)
            distribution.incident = incident

            # Check if there's enough inventory
            inventory = Inventory.objects.get(item=distribution.distribution_type)
            if inventory.quantity_available >= distribution.quantity_requested:
                distribution.save()
                messages.success(request, "Distribution request submitted successfully.")
                return redirect('incident_detail', incident_id=incident.id)
            else:
                messages.error(request, f"Not enough {distribution.distribution_type.name} in inventory. Available: {inventory.quantity_available}")
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = DistributionRequestForm()

    context = {
        'incident': incident,
        'distributions': distributions,
        'form': form,
        'inventories': inventories,
    }

    return render(request, 'incidents/incident_detail.html', context)

# Admin Views
@login_required
def admin_dashboard(request):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to access the admin dashboard.")
        return redirect('dashboard')

    # Get all incidents
    incidents = IncidentReport.objects.all().order_by('-date_reported')

    # Get statistics
    incident_count = incidents.count()
    verified_count = incidents.filter(is_verified=True).count()
    pending_count = incident_count - verified_count

    # Get distribution statistics
    distribution_count = IncidentDistribution.objects.count()
    fulfilled_count = IncidentDistribution.objects.filter(is_fulfilled=True).count()

    # Get disaster type statistics
    disaster_stats = DisasterType.objects.annotate(
        incident_count=Count('incidentreport')
    ).order_by('-incident_count')

    # Get barangay statistics
    barangay_stats = Barangay.objects.annotate(
        incident_count=Count('incidents')
    ).filter(incident_count__gt=0).order_by('-incident_count')

    # Get time-based disaster statistics for line chart
    from django.db.models.functions import TruncMonth, ExtractMonth, ExtractYear

    # Get incidents with date information
    time_incidents = IncidentReport.objects.filter(is_verified=True)

    # Group incidents by month and disaster type
    disaster_time_stats = []

    # Use incident_datetime if available, otherwise use date_reported
    time_incidents_with_datetime = time_incidents.filter(incident_datetime__isnull=False)
    time_incidents_with_date_reported = time_incidents.filter(incident_datetime__isnull=True)

    # Process incidents with incident_datetime
    disaster_month_stats_datetime = time_incidents_with_datetime.annotate(
        month=TruncMonth('incident_datetime'),
        month_name=ExtractMonth('incident_datetime'),
        year=ExtractYear('incident_datetime')
    ).values('disaster_type__name', 'month', 'month_name', 'year').annotate(
        count=Count('id')
    ).order_by('year', 'month_name')

    # Process incidents with only date_reported
    disaster_month_stats_reported = time_incidents_with_date_reported.annotate(
        month=TruncMonth('date_reported'),
        month_name=ExtractMonth('date_reported'),
        year=ExtractYear('date_reported')
    ).values('disaster_type__name', 'month', 'month_name', 'year').annotate(
        count=Count('id')
    ).order_by('year', 'month_name')

    # Combine both sets of statistics
    for stat in list(disaster_month_stats_datetime) + list(disaster_month_stats_reported):
        month_name = {
            1: 'Jan', 2: 'Feb', 3: 'Mar', 4: 'Apr', 5: 'May', 6: 'Jun',
            7: 'Jul', 8: 'Aug', 9: 'Sep', 10: 'Oct', 11: 'Nov', 12: 'Dec'
        }.get(stat['month_name'], 'Unknown')

        disaster_time_stats.append({
            'disaster_type': stat['disaster_type__name'],
            'month': month_name,
            'year': stat['year'],
            'count': stat['count']
        })

    # Paginate incidents
    paginator = Paginator(incidents, 10)  # Show 10 incidents per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'incident_count': incident_count,
        'verified_count': verified_count,
        'pending_count': pending_count,
        'distribution_count': distribution_count,
        'fulfilled_count': fulfilled_count,
        'disaster_stats': disaster_stats,
        'barangay_stats': barangay_stats,
        'disaster_time_stats': disaster_time_stats,
    }

    return render(request, 'dashboard/admin_dashboard.html', context)


@login_required
def verify_incident(request, incident_id):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to verify incidents.")
        return redirect('dashboard')

    incident = get_object_or_404(IncidentReport, id=incident_id)
    incident.verify()

    # Create notification for the incident reporter
    UserNotification.objects.create(
        user=incident.reporter,
        notification_type='incident_verified',
        title='Incident Verified',
        message=f'Your incident report "{incident.title}" has been verified by our team.',
        incident=incident
    )

    messages.success(request, f"Incident '{incident.title}' has been verified.")
    return redirect('admin_dashboard')


@login_required
def deny_incident(request, incident_id):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to deny incidents.")
        return redirect('dashboard')

    incident = get_object_or_404(IncidentReport, id=incident_id)

    if incident.status == 'verified':
        messages.error(request, "Cannot deny an incident that has already been verified.")
        return redirect('incident_detail', incident_id=incident.id)

    if request.method == 'POST':
        form = DenyIncidentForm(request.POST)
        if form.is_valid():
            denial_reason = form.cleaned_data['denial_reason']
            incident.deny(denial_reason)

            # Create notification for the incident reporter
            UserNotification.objects.create(
                user=incident.reporter,
                notification_type='incident_denied',
                title='Incident Denied',
                message=f'Your incident report "{incident.title}" has been denied. Reason: {denial_reason}',
                incident=incident
            )

            messages.success(request, f"Incident '{incident.title}' has been denied.")
            return redirect('admin_dashboard')
    else:
        form = DenyIncidentForm()

    context = {
        'incident': incident,
        'form': form,
    }

    return render(request, 'incidents/deny_incident.html', context)


# Inventory Management Views
@login_required
def inventory_list(request):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to access inventory management.")
        return redirect('dashboard')

    inventories = Inventory.objects.all().order_by('item__name')

    context = {
        'inventories': inventories,
    }

    return render(request, 'inventory/inventory_list.html', context)

@login_required
def update_inventory(request, inventory_id):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to update inventory.")
        return redirect('dashboard')

    inventory = get_object_or_404(Inventory, id=inventory_id)

    if request.method == 'POST':
        form = InventoryForm(request.POST, instance=inventory)
        if form.is_valid():
            form.save()
            messages.success(request, f"Inventory for {inventory.item.name} updated successfully.")
            return redirect('inventory_list')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = InventoryForm(instance=inventory)

    # Get pending distributions for this inventory item
    pending_distributions = IncidentDistribution.objects.filter(
        distribution_type=inventory.item,
        is_fulfilled=False
    )

    context = {
        'form': form,
        'inventory': inventory,
        'pending_distributions': pending_distributions,
        'has_pending': pending_distributions.exists()
    }

    return render(request, 'inventory/update_inventory.html', context)

@login_required
def distribution_list(request):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to access resource request management.")
        return redirect('dashboard')

    distributions = IncidentDistribution.objects.all().order_by('-incident__date_reported')

    # Get counts for badge display
    total_count = distributions.count()
    distributed_count = distributions.filter(status='distributed').count()
    approved_count = distributions.filter(status='approved').count()
    pending_count = distributions.filter(status='pending').count()

    # Get inventory information for each distribution type
    inventories = {inv.item_id: inv.quantity_available for inv in Inventory.objects.all()}

    # Filter by status if provided
    status = request.GET.get('status')
    if status == 'distributed':
        distributions = distributions.filter(status='distributed')
    elif status == 'approved':
        distributions = distributions.filter(status='approved')
    elif status == 'pending':
        distributions = distributions.filter(status='pending')

    # Paginate distributions
    paginator = Paginator(distributions, 10)  # Show 10 distributions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status': status,
        'total_count': total_count,
        'distributed_count': distributed_count,
        'approved_count': approved_count,
        'pending_count': pending_count,
        'inventories': inventories,
    }

    return render(request, 'inventory/distribution_list.html', context)

@login_required
def approve_distribution(request, distribution_id):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to approve distributions.")
        return redirect('dashboard')

    distribution = get_object_or_404(IncidentDistribution, id=distribution_id)

    try:
        distribution.approve_distribution(distribution.quantity_requested)
        messages.success(request, f"Distribution of {distribution.quantity_approved} {distribution.distribution_type.name} approved successfully. It is now pending distribution.")
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('distribution_list')

@login_required
def complete_distribution(request, distribution_id):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to complete distributions.")
        return redirect('dashboard')

    distribution = get_object_or_404(IncidentDistribution, id=distribution_id)

    if distribution.status != 'approved':
        messages.error(request, "Only approved distributions can be completed.")
        return redirect('distribution_list')

    if request.method == 'POST':
        # Collect all distribution data
        distribution_data = {
            'recipient_organization': request.POST.get('recipient_organization', ''),
            'recipient_name': request.POST.get('recipient_name', ''),
            'recipient_contact': request.POST.get('recipient_contact', ''),
            'distributed_by': request.POST.get('distributed_by', ''),
            'distribution_notes': request.POST.get('distribution_notes', '')
        }

        # Process beneficiary list from JSON
        import json
        beneficiary_json = request.POST.get('beneficiary_list', '')
        if beneficiary_json:
            try:
                beneficiaries = json.loads(beneficiary_json)
                # Format the beneficiary list as a readable string
                beneficiary_text = ""
                for beneficiary in beneficiaries:
                    name = beneficiary.get('name', '')
                    household_size = beneficiary.get('household_size', '1')
                    if name:
                        beneficiary_text += f"{name} (Household size: {household_size})\n"
                distribution_data['beneficiary_list'] = beneficiary_text
            except json.JSONDecodeError:
                # If JSON parsing fails, use the raw value
                distribution_data['beneficiary_list'] = beneficiary_json

        # Validate required fields
        if not distribution_data['recipient_name']:
            messages.error(request, "Recipient name is required.")
            return redirect('complete_distribution', distribution_id=distribution_id)

        try:
            distribution.complete_distribution(distribution_data)
            recipient_info = distribution_data['recipient_name']
            if distribution_data['recipient_organization']:
                recipient_info = f"{distribution_data['recipient_name']} from {distribution_data['recipient_organization']}"

            messages.success(request, f"Distribution of {distribution.quantity_approved} {distribution.distribution_type.name} has been completed and distributed to {recipient_info}.")
            return redirect('distribution_list')
        except ValueError as e:
            messages.error(request, str(e))
            return redirect('complete_distribution', distribution_id=distribution_id)

    # Get inventory information
    inventory = Inventory.objects.get(item=distribution.distribution_type)

    # Get user profile for barangay information
    try:
        user_profile = request.user.reporterprofile
    except:
        user_profile = None

    context = {
        'distribution': distribution,
        'inventory': inventory,
        'current_user': request.user.get_full_name() or request.user.username,
        'user_profile': user_profile,
    }

    return render(request, 'inventory/complete_distribution.html', context)

@login_required
def distribution_detail(request, distribution_id):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to view distribution details.")
        return redirect('dashboard')

    distribution = get_object_or_404(IncidentDistribution, id=distribution_id)

    context = {
        'distribution': distribution,
    }

    return render(request, 'inventory/distribution_detail.html', context)

@login_required
def distribution_management(request):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to access distribution management.")
        return redirect('dashboard')

    distributions = IncidentDistribution.objects.all().order_by('-id')
    resource_types = DistributionType.objects.all()

    # Apply filters
    filters = {}
    active_filters = []

    # Search filter (searches across multiple fields)
    search_query = request.GET.get('search', '')
    if search_query:
        from django.db.models import Q
        distributions = distributions.filter(
            Q(incident__title__icontains=search_query) |
            Q(distribution_type__name__icontains=search_query) |
            Q(recipient_name__icontains=search_query) |
            Q(recipient_organization__icontains=search_query) |
            Q(distributed_by__icontains=search_query)
        )
        active_filters.append(f"Search: {search_query}")

    # Status filter
    status = request.GET.get('status', '')
    if status:
        distributions = distributions.filter(status=status)
        status_display = dict(IncidentDistribution.STATUS_CHOICES).get(status, status)
        active_filters.append(f"Status: {status_display}")

    # Resource type filter
    resource_type = request.GET.get('resource_type', '')
    if resource_type:
        distributions = distributions.filter(distribution_type_id=resource_type)
        resource_type_obj = DistributionType.objects.filter(id=resource_type).first()
        if resource_type_obj:
            active_filters.append(f"Resource Type: {resource_type_obj.name}")

    # Recipient organization filter
    recipient_org = request.GET.get('recipient_org', '')
    if recipient_org:
        distributions = distributions.filter(recipient_organization__icontains=recipient_org)
        active_filters.append(f"Organization: {recipient_org}")

    # Recipient name filter
    recipient_name = request.GET.get('recipient_name', '')
    if recipient_name:
        distributions = distributions.filter(recipient_name__icontains=recipient_name)
        active_filters.append(f"Recipient: {recipient_name}")

    # Beneficiary filter
    beneficiary = request.GET.get('beneficiary', '')
    if beneficiary:
        distributions = distributions.filter(beneficiary_list__icontains=beneficiary)
        active_filters.append(f"Beneficiary: {beneficiary}")

    # Date range filter
    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if date_from:
        distributions = distributions.filter(distribution_date__gte=date_from)
        active_filters.append(f"From: {date_from}")

    if date_to:
        distributions = distributions.filter(distribution_date__lte=date_to)
        active_filters.append(f"To: {date_to}")

    # Pagination
    paginator = Paginator(distributions, 20)  # Show 20 distributions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'distributions': page_obj,
        'resource_types': resource_types,
        'active_filters': ', '.join(active_filters) if active_filters else None,
    }

    return render(request, 'inventory/distribution_management.html', context)

@login_required
def export_distributions(request):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to export distribution data.")
        return redirect('dashboard')

    # Get distributions with the same filters as the management page
    distributions = IncidentDistribution.objects.all().order_by('-id')

    # Apply filters (same as in distribution_management)
    search_query = request.GET.get('search', '')
    if search_query:
        from django.db.models import Q
        distributions = distributions.filter(
            Q(incident__title__icontains=search_query) |
            Q(distribution_type__name__icontains=search_query) |
            Q(recipient_name__icontains=search_query) |
            Q(recipient_organization__icontains=search_query) |
            Q(distributed_by__icontains=search_query)
        )

    status = request.GET.get('status', '')
    if status:
        distributions = distributions.filter(status=status)

    resource_type = request.GET.get('resource_type', '')
    if resource_type:
        distributions = distributions.filter(distribution_type_id=resource_type)

    recipient_org = request.GET.get('recipient_org', '')
    if recipient_org:
        distributions = distributions.filter(recipient_organization__icontains=recipient_org)

    recipient_name = request.GET.get('recipient_name', '')
    if recipient_name:
        distributions = distributions.filter(recipient_name__icontains=recipient_name)

    beneficiary = request.GET.get('beneficiary', '')
    if beneficiary:
        distributions = distributions.filter(beneficiary_list__icontains=beneficiary)

    date_from = request.GET.get('date_from', '')
    date_to = request.GET.get('date_to', '')

    if date_from:
        distributions = distributions.filter(distribution_date__gte=date_from)

    if date_to:
        distributions = distributions.filter(distribution_date__lte=date_to)

    # Generate PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="distribution_report.pdf"'

    # Create the PDF
    buffer = generate_distribution_pdf(distributions)

    # Write the PDF to the response
    response.write(buffer.getvalue())
    buffer.close()

    return response

def generate_distribution_pdf(distributions):
    """Generate a PDF report of distributions"""
    buffer = io.BytesIO()

    # Import ReportLab components
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER
    import os
    from django.conf import settings

    # Create the PDF object
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)

    # Container for the 'Flowable' objects
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    # Create custom styles with different names to avoid conflicts
    title_style = ParagraphStyle(name='CustomTitle', parent=styles['Title'], alignment=TA_CENTER, fontSize=16, fontName='Helvetica-Bold')
    subtitle_style = ParagraphStyle(name='CustomSubtitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle(name='CustomNormal', parent=styles['Normal'], fontSize=10, fontName='Helvetica')

    # Add logo if available
    logo_path = os.path.join(settings.STATIC_ROOT, 'img', 'logo.png')
    if os.path.exists(logo_path):
        img = Image(logo_path, width=1.5*inch, height=1.5*inch)
        elements.append(img)

    # Add title
    elements.append(Paragraph("Distribution Report", title_style))
    elements.append(Spacer(1, 0.25*inch))

    # Add date
    from django.utils import timezone
    current_date = timezone.now().strftime("%B %d, %Y")
    elements.append(Paragraph(f"Generated on: {current_date}", subtitle_style))
    elements.append(Spacer(1, 0.25*inch))

    # Create table data
    data = [
        ['ID', 'Incident', 'Resource Type', 'Quantity', 'Status', 'Recipient', 'Organization', 'Date']
    ]

    # Add distribution data
    for dist in distributions:
        status_map = {
            'pending': 'Pending',
            'approved': 'Approved',
            'distributed': 'Distributed'
        }

        data.append([
            str(dist.id),
            dist.incident.title[:30] + ('...' if len(dist.incident.title) > 30 else ''),
            dist.distribution_type.name,
            f"{dist.quantity_approved} / {dist.quantity_requested}",
            status_map.get(dist.status, dist.status),
            dist.recipient_name or '-',
            dist.recipient_organization or '-',
            dist.distribution_date.strftime("%m/%d/%Y") if dist.distribution_date else '-'
        ])

    # Create the table
    table = Table(data, repeatRows=1)

    # Add style to the table
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))

    # Add the table to the elements
    elements.append(table)

    # Add summary information
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(f"Total Records: {len(distributions)}", normal_style))

    # Count by status
    status_counts = {}
    for dist in distributions:
        status_counts[dist.status] = status_counts.get(dist.status, 0) + 1

    for status, count in status_counts.items():
        status_display = {
            'pending': 'Pending',
            'approved': 'Approved',
            'distributed': 'Distributed'
        }.get(status, status)
        elements.append(Paragraph(f"{status_display}: {count}", normal_style))

    # Build the PDF
    doc.build(elements)

    # Get the value of the BytesIO buffer
    buffer.seek(0)
    return buffer

# API Views for HTMX
def recent_incidents_api(request):
    recent_incidents = IncidentReport.objects.filter(is_verified=True).order_by('-date_reported')[:3]
    return render(request, 'api/recent_incidents.html', {'incidents': recent_incidents})

@login_required
def mark_notification_read(request, notification_id):
    notification = get_object_or_404(UserNotification, id=notification_id, user=request.user)
    notification.mark_as_read()

    # Redirect back to the referring page or dashboard
    next_url = request.GET.get('next', 'dashboard')
    return redirect(next_url)

# Report Views
@login_required
def report_list(request):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to access the reports section.")
        return redirect('dashboard')

    # Get filter parameters
    disaster_type = request.GET.get('disaster_type')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    # Start with all incidents
    incidents = IncidentReport.objects.all().order_by('-date_reported')

    # Apply filters
    if disaster_type:
        incidents = incidents.filter(disaster_type__id=disaster_type)

    if status:
        if status == 'verified':
            incidents = incidents.filter(is_verified=True)
        elif status == 'pending':
            incidents = incidents.filter(is_verified=False, status='pending')
        elif status == 'denied':
            incidents = incidents.filter(status='denied')

    if date_from:
        incidents = incidents.filter(date_reported__gte=date_from)

    if date_to:
        incidents = incidents.filter(date_reported__lte=date_to)

    # Get disaster types for filter dropdown
    disaster_types = DisasterType.objects.all()

    # Paginate results
    paginator = Paginator(incidents, 10)  # Show 10 incidents per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'disaster_types': disaster_types,
        'current_filters': {
            'disaster_type': disaster_type,
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
        }
    }

    return render(request, 'reports/report_list.html', context)

@login_required
def export_report(request):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to export reports.")
        return redirect('dashboard')

    # Get filter parameters
    disaster_type = request.GET.get('disaster_type')
    status = request.GET.get('status')
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    export_format = request.GET.get('format', 'pdf')

    # Get disaster types for filter dropdown
    disaster_types = DisasterType.objects.all()

    # If form is submitted, generate the report
    if 'generate' in request.GET:
        # Start with all incidents
        incidents = IncidentReport.objects.all().order_by('-date_reported')

        # Apply filters
        if disaster_type:
            incidents = incidents.filter(disaster_type__id=disaster_type)

        if status:
            if status == 'verified':
                incidents = incidents.filter(is_verified=True)
            elif status == 'pending':
                incidents = incidents.filter(is_verified=False, status='pending')
            elif status == 'denied':
                incidents = incidents.filter(status='denied')

        if date_from:
            incidents = incidents.filter(date_reported__gte=date_from)

        if date_to:
            incidents = incidents.filter(date_reported__lte=date_to)

        # Check if there are any incidents matching the criteria
        if not incidents.exists():
            messages.warning(request, "No incidents found matching your criteria. Please try different filters.")
            return render(request, 'reports/no_reports.html')

        # Generate PDF report
        if export_format == 'pdf':
            return generate_pdf_report(request, incidents)

    context = {
        'disaster_types': disaster_types,
        'current_filters': {
            'disaster_type': disaster_type,
            'status': status,
            'date_from': date_from,
            'date_to': date_to,
        }
    }

    return render(request, 'reports/export_report.html', context)

def generate_pdf_report(request, incidents):
    # Create a file-like buffer to receive PDF data
    buffer = io.BytesIO()

    # Import ReportLab components
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    import os
    from django.conf import settings

    # Create the PDF object, using the buffer as its "file"
    doc = SimpleDocTemplate(buffer, pagesize=letter)

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=12
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=12
    )

    # Add the logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'logo', 'mdrrmc_logo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path)
        logo.drawHeight = 0.8 * inch
        logo.drawWidth = 0.8 * inch
        elements.append(logo)

    # Add title
    title = Paragraph("Incident Report Summary", title_style)
    elements.append(title)
    elements.append(Spacer(1, 0.25 * inch))

    # Add date range info
    date_info = Paragraph(f"Report generated on: {timezone.now().strftime('%B %d, %Y')}", subtitle_style)
    elements.append(date_info)
    elements.append(Spacer(1, 0.25 * inch))

    # Create table data
    data = [
        ['ID', 'Title', 'Location', 'Disaster Type', 'Date Reported', 'Status']
    ]

    # Add incident data to table
    for incident in incidents:
        status = "Verified" if incident.is_verified else incident.status.capitalize()
        location = incident.barangay.name if incident.barangay else incident.location

        data.append([
            str(incident.id),
            incident.title,
            location,
            incident.disaster_type.name,
            incident.date_reported.strftime('%Y-%m-%d'),
            status
        ])

    # Create the table
    table = Table(data, repeatRows=1)

    # Add style to table
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(table)

    # Add summary statistics
    elements.append(Spacer(1, 0.5 * inch))
    elements.append(Paragraph("Summary Statistics:", styles["Heading3"]))
    elements.append(Spacer(1, 0.1 * inch))

    verified_count = sum(1 for incident in incidents if incident.is_verified)
    pending_count = sum(1 for incident in incidents if incident.status == 'pending')
    denied_count = sum(1 for incident in incidents if incident.status == 'denied')

    stats_data = [
        ['Total Incidents', 'Verified', 'Pending', 'Denied'],
        [str(len(incidents)), str(verified_count), str(pending_count), str(denied_count)]
    ]

    stats_table = Table(stats_data)
    stats_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(stats_table)

    # Build the PDF
    doc.build(elements)

    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()

    # Create the HttpResponse object with the appropriate PDF headers
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="incident_report.pdf"'

    return response


# Disaster Alert Views
@login_required
def create_alert(request):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to create disaster alerts.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = DisasterAlertForm(request.POST)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.created_by = request.user
            alert.save()

            messages.success(request, f"Disaster alert '{alert.title}' has been created and is now active.")
            return redirect('manage_alerts')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = DisasterAlertForm()

    return render(request, 'admin/create_alert.html', {'form': form})


@login_required
def manage_alerts(request):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to manage disaster alerts.")
        return redirect('dashboard')

    alerts = DisasterAlert.objects.all().order_by('-created_at')

    return render(request, 'admin/manage_alerts.html', {'alerts': alerts})


@login_required
def deactivate_alert(request, alert_id):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to deactivate disaster alerts.")
        return redirect('dashboard')

    alert = get_object_or_404(DisasterAlert, id=alert_id)

    if request.method == 'POST':
        alert.is_active = False
        alert.save()
        messages.success(request, f"Disaster alert '{alert.title}' has been deactivated.")

    return redirect('manage_alerts')


@login_required
def activate_alert(request, alert_id):
    if not request.user.is_staff:
        messages.error(request, "You are not authorized to activate disaster alerts.")
        return redirect('dashboard')

    alert = get_object_or_404(DisasterAlert, id=alert_id)

    if request.method == 'POST':
        alert.is_active = True
        alert.save()
        messages.success(request, f"Disaster alert '{alert.title}' has been activated.")

    return redirect('manage_alerts')


# Evacuation Center Management Views
@login_required
def evacuation_center_list(request):
    # Check if user is a barangay captain or admin
    is_barangay_captain = False
    user_barangay = None

    try:
        profile = request.user.reporterprofile
        # Debug information to help diagnose the issue
        print(f"DEBUG - User: {request.user.username}")
        print(f"DEBUG - Has profile: {hasattr(request.user, 'reporterprofile')}")
        if hasattr(request.user, 'reporterprofile'):
            print(f"DEBUG - Profile barangay: {profile.barangay}")
            print(f"DEBUG - Is barangay captain: {profile.is_barangay_captain}")

        # All registered users with a barangay are barangay captains
        if profile.barangay:
            is_barangay_captain = True
            user_barangay = profile.barangay

            # Ensure the is_barangay_captain flag is set correctly
            if not profile.is_barangay_captain:
                profile.is_barangay_captain = True
                profile.save()
                print(f"DEBUG - Updated is_barangay_captain flag for {request.user.username}")
    except Exception as e:
        print(f"DEBUG - Exception in evacuation_center_list: {str(e)}")
        import traceback
        print(traceback.format_exc())

    # If not admin or barangay captain, redirect to dashboard
    if not request.user.is_staff and not is_barangay_captain:
        messages.error(request, "You are not authorized to access evacuation center management.")
        return redirect('dashboard')

    # Get evacuation centers based on user role
    if request.user.is_staff:
        # Admin can see all centers
        centers = EvacuationCenter.objects.all().order_by('barangay__name', 'name')
    else:
        # Barangay captain can only see centers in their barangay
        centers = EvacuationCenter.objects.filter(barangay=user_barangay).order_by('name')

    # Apply filters
    status = request.GET.get('status')
    if status:
        centers = centers.filter(status=status)

    barangay_id = request.GET.get('barangay')
    if barangay_id and request.user.is_staff:  # Only staff can filter by barangay
        centers = centers.filter(barangay_id=barangay_id)

    # Pagination
    paginator = Paginator(centers, 10)  # Show 10 centers per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Get all barangays for filter dropdown (admin only)
    barangays = Barangay.objects.all().order_by('name') if request.user.is_staff else None

    context = {
        'page_obj': page_obj,
        'barangays': barangays,
        'status': status,
        'selected_barangay': barangay_id,
        'is_barangay_captain': is_barangay_captain,
        'user_barangay': user_barangay,
    }

    return render(request, 'evacuation/evacuation_center_list.html', context)


@login_required
def evacuation_center_detail(request, center_id):
    # Get the evacuation center
    center = get_object_or_404(EvacuationCenter, id=center_id)

    # Check if user is authorized to view this center
    is_authorized = False
    is_barangay_captain = False

    if request.user.is_staff:
        is_authorized = True
    else:
        try:
            profile = request.user.reporterprofile
            # Debug information to help diagnose the issue
            print(f"DEBUG - Detail view - User: {request.user.username}")
            print(f"DEBUG - Detail view - Has profile: {hasattr(request.user, 'reporterprofile')}")
            if hasattr(request.user, 'reporterprofile'):
                print(f"DEBUG - Detail view - Profile barangay: {profile.barangay}")
                print(f"DEBUG - Detail view - Center barangay: {center.barangay}")
                print(f"DEBUG - Detail view - Is barangay captain: {profile.is_barangay_captain}")

            # All registered users with a barangay are barangay captains
            if profile.barangay:
                is_barangay_captain = True

                # If the user is a barangay captain for this center's barangay, they're authorized
                if profile.barangay == center.barangay:
                    is_authorized = True

                # Ensure the is_barangay_captain flag is set correctly
                if not profile.is_barangay_captain:
                    profile.is_barangay_captain = True
                    profile.save()
                    print(f"DEBUG - Detail view - Updated is_barangay_captain flag for {request.user.username}")
        except Exception as e:
            print(f"DEBUG - Exception in evacuation_center_detail: {str(e)}")
            import traceback
            print(traceback.format_exc())

    if not is_authorized:
        messages.error(request, "You are not authorized to view this evacuation center.")
        return redirect('dashboard')

    # Get evacuees in this center
    evacuees = Evacuee.objects.filter(evacuation_center=center, date_departed__isnull=True).order_by('family_name', 'name')

    # Group evacuees by family
    families = {}
    for evacuee in evacuees:
        family_name = evacuee.family_name or 'Unspecified'
        if family_name not in families:
            families[family_name] = []
        families[family_name].append(evacuee)

    context = {
        'center': center,
        'evacuees': evacuees,
        'families': families,
        'evacuee_count': evacuees.count(),
        'family_count': len(families),
        'is_barangay_captain': is_barangay_captain,
    }

    return render(request, 'evacuation/evacuation_center_detail.html', context)


@login_required
def create_evacuation_center(request):
    # Check if user is a barangay captain
    is_barangay_captain = False

    try:
        profile = request.user.reporterprofile
        # Debug information to help diagnose the issue
        print(f"DEBUG - Create view - User: {request.user.username}")
        print(f"DEBUG - Create view - Has profile: {hasattr(request.user, 'reporterprofile')}")
        if hasattr(request.user, 'reporterprofile'):
            print(f"DEBUG - Create view - Profile barangay: {profile.barangay}")
            print(f"DEBUG - Create view - Is barangay captain: {profile.is_barangay_captain}")

        # All registered users with a barangay are barangay captains
        if profile.barangay:
            is_barangay_captain = True

            # Ensure the is_barangay_captain flag is set correctly
            if not profile.is_barangay_captain:
                profile.is_barangay_captain = True
                profile.save()
                print(f"DEBUG - Create view - Updated is_barangay_captain flag for {request.user.username}")
    except Exception as e:
        print(f"DEBUG - Exception in create_evacuation_center: {str(e)}")
        import traceback
        print(traceback.format_exc())

    # Only barangay captains can create evacuation centers
    if not is_barangay_captain:
        if request.user.is_staff:
            messages.info(request, "Admin users can only view evacuation centers. Creation is reserved for barangay captains.")
        else:
            messages.error(request, "You are not authorized to create evacuation centers. Only barangay captains can create evacuation centers.")
        return redirect('evacuation_center_list')

    if request.method == 'POST':
        form = EvacuationCenterForm(request.POST, user=request.user)
        if form.is_valid():
            center = form.save(commit=False)

            # Set the manager to the current user (barangay captain)
            center.manager = request.user

            # Ensure the barangay is set to the captain's barangay
            center.barangay = request.user.reporterprofile.barangay

            center.save()

            # Notify admin users about the new evacuation center
            for admin_user in User.objects.filter(is_staff=True):
                UserNotification.objects.create(
                    user=admin_user,
                    notification_type='evacuation_update',
                    title='New Evacuation Center Created',
                    message=f"A new evacuation center '{center.name}' has been created in {center.barangay.name} by {request.user.get_full_name() or request.user.username}.",
                    evacuation_center=center
                )

            messages.success(request, f"Evacuation center '{center.name}' has been created successfully.")
            return redirect('evacuation_center_detail', center_id=center.id)
    else:
        form = EvacuationCenterForm(user=request.user)

    context = {
        'form': form,
        'is_barangay_captain': is_barangay_captain,
    }

    return render(request, 'evacuation/create_evacuation_center.html', context)


@login_required
def update_evacuation_center(request, center_id):
    # Get the evacuation center
    center = get_object_or_404(EvacuationCenter, id=center_id)

    # Check if user is authorized to update this center
    is_authorized = False
    if request.user.is_staff:
        is_authorized = True
    else:
        try:
            profile = request.user.reporterprofile
            if profile.is_barangay_captain and profile.barangay == center.barangay:
                is_authorized = True
        except:
            pass

    if not is_authorized:
        messages.error(request, "You are not authorized to update this evacuation center.")
        return redirect('dashboard')

    if request.method == 'POST':
        form = EvacuationCenterForm(request.POST, instance=center, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f"Evacuation center '{center.name}' has been updated successfully.")
            return redirect('evacuation_center_detail', center_id=center.id)
    else:
        form = EvacuationCenterForm(instance=center, user=request.user)

    context = {
        'form': form,
        'center': center,
    }

    return render(request, 'evacuation/update_evacuation_center.html', context)


@login_required
def activate_evacuation_center(request, center_id):
    # Get the evacuation center
    center = get_object_or_404(EvacuationCenter, id=center_id)

    # Check if user is authorized to activate this center
    is_authorized = False
    if request.user.is_staff:
        is_authorized = True
    else:
        try:
            profile = request.user.reporterprofile
            if profile.is_barangay_captain and profile.barangay == center.barangay:
                is_authorized = True
        except:
            pass

    if not is_authorized:
        messages.error(request, "You are not authorized to activate this evacuation center.")
        return redirect('dashboard')

    # Activate the center
    center.activate()

    # Create notifications for admin users
    if not request.user.is_staff:
        for admin_user in User.objects.filter(is_staff=True):
            UserNotification.objects.create(
                user=admin_user,
                notification_type='evacuation_activated',
                title='Evacuation Center Activated',
                message=f"Evacuation center '{center.name}' in {center.barangay.name} has been activated by {request.user.get_full_name() or request.user.username}.",
                evacuation_center=center
            )

    messages.success(request, f"Evacuation center '{center.name}' has been activated.")
    return redirect('evacuation_center_detail', center_id=center.id)


@login_required
def deactivate_evacuation_center(request, center_id):
    # Get the evacuation center
    center = get_object_or_404(EvacuationCenter, id=center_id)

    # Check if user is authorized to deactivate this center
    is_authorized = False
    if request.user.is_staff:
        is_authorized = True
    else:
        try:
            profile = request.user.reporterprofile
            if profile.is_barangay_captain and profile.barangay == center.barangay:
                is_authorized = True
        except:
            pass

    if not is_authorized:
        messages.error(request, "You are not authorized to deactivate this evacuation center.")
        return redirect('dashboard')

    # Deactivate the center
    center.deactivate()

    messages.success(request, f"Evacuation center '{center.name}' has been set to standby mode.")
    return redirect('evacuation_center_detail', center_id=center.id)


@login_required
def close_evacuation_center(request, center_id):
    # Get the evacuation center
    center = get_object_or_404(EvacuationCenter, id=center_id)

    # Check if user is authorized to close this center
    is_authorized = False
    if request.user.is_staff:
        is_authorized = True
    else:
        try:
            profile = request.user.reporterprofile
            if profile.is_barangay_captain and profile.barangay == center.barangay:
                is_authorized = True
        except:
            pass

    if not is_authorized:
        messages.error(request, "You are not authorized to close this evacuation center.")
        return redirect('dashboard')

    # Check if there are still evacuees
    active_evacuees = Evacuee.objects.filter(evacuation_center=center, date_departed__isnull=True).count()
    if active_evacuees > 0:
        messages.error(request, f"Cannot close evacuation center. There are still {active_evacuees} active evacuees.")
        return redirect('evacuation_center_detail', center_id=center.id)

    # Close the center
    center.close()

    messages.success(request, f"Evacuation center '{center.name}' has been closed.")
    return redirect('evacuation_center_list')


@login_required
def add_evacuee(request, center_id):
    # Get the evacuation center
    center = get_object_or_404(EvacuationCenter, id=center_id)

    # Check if user is authorized to add evacuees to this center
    is_authorized = False
    if request.user.is_staff:
        is_authorized = True
    else:
        try:
            profile = request.user.reporterprofile
            # Debug information to help diagnose the issue
            print(f"DEBUG - Add evacuee - User: {request.user.username}")
            print(f"DEBUG - Add evacuee - Has profile: {hasattr(request.user, 'reporterprofile')}")
            if hasattr(request.user, 'reporterprofile'):
                print(f"DEBUG - Add evacuee - Profile barangay: {profile.barangay}")
                print(f"DEBUG - Add evacuee - Center barangay: {center.barangay}")
                print(f"DEBUG - Add evacuee - Is barangay captain: {profile.is_barangay_captain}")

            # All registered users with a barangay are barangay captains
            if profile.barangay and profile.barangay == center.barangay:
                is_authorized = True

                # Ensure the is_barangay_captain flag is set correctly
                if not profile.is_barangay_captain:
                    profile.is_barangay_captain = True
                    profile.save()
                    print(f"DEBUG - Add evacuee - Updated is_barangay_captain flag for {request.user.username}")
        except Exception as e:
            print(f"DEBUG - Exception in add_evacuee: {str(e)}")
            import traceback
            print(traceback.format_exc())

    if not is_authorized:
        messages.error(request, "You are not authorized to add evacuees to this center.")
        return redirect('dashboard')

    # Check if center is active
    if center.status != 'active':
        messages.error(request, "Cannot add evacuees to a center that is not active.")
        return redirect('evacuation_center_detail', center_id=center.id)

    # Check if center is at capacity
    if center.current_occupancy >= center.capacity:
        messages.error(request, "This evacuation center is at full capacity.")
        return redirect('evacuation_center_detail', center_id=center.id)

    if request.method == 'POST':
        form = EvacueeForm(request.POST, user=request.user, center_id=center.id)
        if form.is_valid():
            evacuee = form.save(commit=False)
            evacuee.evacuation_center = center
            evacuee.save()

            # Update center occupancy
            center.current_occupancy += 1
            center.save()

            messages.success(request, f"{evacuee.name} has been added to the evacuation center.")
            return redirect('evacuation_center_detail', center_id=center.id)
    else:
        form = EvacueeForm(user=request.user, center_id=center.id)

    context = {
        'form': form,
        'center': center,
    }

    return render(request, 'evacuation/add_evacuee.html', context)


@login_required
def evacuee_departure(request, evacuee_id):
    # Get the evacuee
    evacuee = get_object_or_404(Evacuee, id=evacuee_id)
    center = evacuee.evacuation_center

    # Check if user is authorized to manage this evacuee
    is_authorized = False
    if request.user.is_staff:
        is_authorized = True
    else:
        try:
            profile = request.user.reporterprofile
            # Debug information to help diagnose the issue
            print(f"DEBUG - Evacuee departure - User: {request.user.username}")
            print(f"DEBUG - Evacuee departure - Has profile: {hasattr(request.user, 'reporterprofile')}")
            if hasattr(request.user, 'reporterprofile'):
                print(f"DEBUG - Evacuee departure - Profile barangay: {profile.barangay}")
                print(f"DEBUG - Evacuee departure - Center barangay: {center.barangay}")
                print(f"DEBUG - Evacuee departure - Is barangay captain: {profile.is_barangay_captain}")

            # All registered users with a barangay are barangay captains
            if profile.barangay and profile.barangay == center.barangay:
                is_authorized = True

                # Ensure the is_barangay_captain flag is set correctly
                if not profile.is_barangay_captain:
                    profile.is_barangay_captain = True
                    profile.save()
                    print(f"DEBUG - Evacuee departure - Updated is_barangay_captain flag for {request.user.username}")
        except Exception as e:
            print(f"DEBUG - Exception in evacuee_departure: {str(e)}")
            import traceback
            print(traceback.format_exc())

    if not is_authorized:
        messages.error(request, "You are not authorized to manage evacuees in this center.")
        return redirect('dashboard')

    # Record departure
    evacuee.depart()

    messages.success(request, f"{evacuee.name} has been marked as departed from the evacuation center.")
    return redirect('evacuation_center_detail', center_id=center.id)


@login_required
def generate_evacuation_report(request, center_id):
    # Get the evacuation center
    center = get_object_or_404(EvacuationCenter, id=center_id)

    # Check if user is authorized to generate reports for this center
    is_authorized = False
    if request.user.is_staff:
        is_authorized = True
    else:
        try:
            profile = request.user.reporterprofile
            # Debug information to help diagnose the issue
            print(f"DEBUG - Generate report - User: {request.user.username}")
            print(f"DEBUG - Generate report - Has profile: {hasattr(request.user, 'reporterprofile')}")
            if hasattr(request.user, 'reporterprofile'):
                print(f"DEBUG - Generate report - Profile barangay: {profile.barangay}")
                print(f"DEBUG - Generate report - Center barangay: {center.barangay}")
                print(f"DEBUG - Generate report - Is barangay captain: {profile.is_barangay_captain}")

            # All registered users with a barangay are barangay captains
            if profile.barangay and profile.barangay == center.barangay:
                is_authorized = True

                # Ensure the is_barangay_captain flag is set correctly
                if not profile.is_barangay_captain:
                    profile.is_barangay_captain = True
                    profile.save()
                    print(f"DEBUG - Generate report - Updated is_barangay_captain flag for {request.user.username}")
        except Exception as e:
            print(f"DEBUG - Exception in generate_evacuation_report: {str(e)}")
            import traceback
            print(traceback.format_exc())

    if not is_authorized:
        messages.error(request, "You are not authorized to generate reports for this center.")
        return redirect('dashboard')

    # Get evacuees in this center
    evacuees = Evacuee.objects.filter(evacuation_center=center).order_by('family_name', 'name')

    # Generate PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="evacuation_report_{center.id}.pdf"'

    # Create the PDF
    buffer = generate_evacuation_pdf(center, evacuees)

    # Write the PDF to the response
    response.write(buffer.getvalue())
    buffer.close()

    return response


def generate_evacuation_pdf(center, evacuees):
    """Generate a PDF report of an evacuation center"""
    buffer = io.BytesIO()

    # Import ReportLab components
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER
    import os
    from django.conf import settings

    # Create the PDF object
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=72)

    # Container for the 'Flowable' objects
    elements = []

    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(name='CustomTitle', parent=styles['Title'], alignment=TA_CENTER, fontSize=16, fontName='Helvetica-Bold')
    subtitle_style = ParagraphStyle(name='CustomSubtitle', parent=styles['Normal'], alignment=TA_CENTER, fontSize=12, fontName='Helvetica-Bold')
    normal_style = ParagraphStyle(name='CustomNormal', parent=styles['Normal'], fontSize=10, fontName='Helvetica')

    # Add logo if available
    logo_path = os.path.join(settings.STATIC_ROOT, 'img', 'logo.png')
    if os.path.exists(logo_path):
        img = Image(logo_path, width=1.5*inch, height=1.5*inch)
        elements.append(img)

    # Add title
    elements.append(Paragraph(f"Evacuation Center Report: {center.name}", title_style))
    elements.append(Spacer(1, 0.25*inch))

    # Add date
    from django.utils import timezone
    current_date = timezone.now().strftime("%B %d, %Y")
    elements.append(Paragraph(f"Generated on: {current_date}", subtitle_style))
    elements.append(Spacer(1, 0.25*inch))

    # Add center details
    elements.append(Paragraph("Evacuation Center Details", subtitle_style))
    elements.append(Spacer(1, 0.1*inch))

    center_data = [
        ['Barangay:', center.barangay.name],
        ['Address:', center.address],
        ['Capacity:', str(center.capacity)],
        ['Current Occupancy:', str(center.current_occupancy)],
        ['Status:', center.get_status_display()],
        ['Manager:', center.manager.get_full_name() if center.manager else 'Not assigned'],
        ['Contact Info:', center.contact_info or 'Not provided'],
        ['Facilities:', center.facilities or 'Not specified'],
    ]

    center_table = Table(center_data, colWidths=[1.5*inch, 4*inch])
    center_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
        ('ALIGN', (0, 0), (0, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (0, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    elements.append(center_table)
    elements.append(Spacer(1, 0.25*inch))

    # Add evacuee list
    elements.append(Paragraph("Evacuee List", subtitle_style))
    elements.append(Spacer(1, 0.1*inch))

    # Create table data
    evacuee_data = [
        ['Name', 'Age', 'Gender', 'Family', 'Special Needs', 'Status']
    ]

    # Add evacuee data
    for evacuee in evacuees:
        status = 'Active' if not evacuee.date_departed else f"Departed on {evacuee.date_departed.strftime('%m/%d/%Y')}"
        evacuee_data.append([
            evacuee.name,
            str(evacuee.age),
            evacuee.get_gender_display(),
            evacuee.family_name or '-',
            evacuee.special_needs or '-',
            status
        ])

    # Create the table
    evacuee_table = Table(evacuee_data, repeatRows=1)

    # Add style to the table
    evacuee_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
    ]))

    elements.append(evacuee_table)

    # Add summary information
    elements.append(Spacer(1, 0.5*inch))
    elements.append(Paragraph(f"Total Evacuees: {evacuees.count()}", normal_style))

    # Count active evacuees
    active_count = sum(1 for e in evacuees if not e.date_departed)
    elements.append(Paragraph(f"Active Evacuees: {active_count}", normal_style))
    elements.append(Paragraph(f"Departed Evacuees: {evacuees.count() - active_count}", normal_style))

    # Count families
    families = set(e.family_name for e in evacuees if e.family_name)
    elements.append(Paragraph(f"Number of Families: {len(families)}", normal_style))

    # Build the PDF
    doc.build(elements)

    # Get the value of the BytesIO buffer
    buffer.seek(0)
    return buffer


# Custom error handlers
def handler404(request, exception):
    """
    Custom 404 error handler that renders our 404.html template
    """
    return render(request, '404.html', status=404)


@login_required
def comprehensive_view(request):
    """
    Comprehensive view that displays all data from the models in a single page
    """
    # Check if user is admin
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')

    # Get all data from models
    municipalities = Municipality.objects.all().prefetch_related('barangays')
    disaster_types = DisasterType.objects.all()
    distribution_types = DistributionType.objects.all().select_related('inventory')
    evacuation_centers = EvacuationCenter.objects.all().select_related('barangay', 'manager')
    incidents = IncidentReport.objects.all().select_related('reporter', 'disaster_type', 'barangay')
    alerts = DisasterAlert.objects.all().select_related('created_by')

    context = {
        'municipalities': municipalities,
        'disaster_types': disaster_types,
        'distribution_types': distribution_types,
        'evacuation_centers': evacuation_centers,
        'incidents': incidents,
        'alerts': alerts,
    }

    return render(request, 'admin/comprehensive_view.html', context)


@login_required
def consolidated_table_view(request):
    """
    Consolidated table view that displays barangay data with related information
    in a single table format
    """
    # Check if user is admin
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')

    # Get all barangays with prefetched related data
    barangays = Barangay.objects.all().select_related('municipality')

    # Prepare consolidated data
    consolidated_data = []

    for barangay in barangays:
        # Get barangay captain
        captain = User.objects.filter(
            reporterprofile__barangay=barangay,
            reporterprofile__is_barangay_captain=True
        ).first()

        # Get evacuation centers for this barangay
        centers = EvacuationCenter.objects.filter(barangay=barangay)

        # Get incidents for this barangay
        incidents = IncidentReport.objects.filter(barangay=barangay)
        verified_incidents = incidents.filter(status='verified').count()
        pending_incidents = incidents.filter(status='pending').count()

        # Get distributions related to incidents in this barangay
        incident_ids = incidents.values_list('id', flat=True)
        distributions = IncidentDistribution.objects.filter(incident__in=incident_ids)
        fulfilled_distributions = distributions.filter(status='distributed').count()
        pending_distributions = distributions.filter(status='pending').count()

        # Get evacuees from evacuation centers in this barangay
        center_ids = centers.values_list('id', flat=True)
        evacuees = Evacuee.objects.filter(evacuation_center__in=center_ids)
        active_evacuees = evacuees.filter(date_departed__isnull=True)

        # Calculate total evacuees (currently in centers)
        total_evacuees = active_evacuees.count()

        # Add to consolidated data
        consolidated_data.append({
            'barangay': barangay,
            'captain': captain,
            'evacuation_centers': centers,
            'incidents': incidents,
            'verified_incidents': verified_incidents,
            'pending_incidents': pending_incidents,
            'distributions': distributions,
            'fulfilled_distributions': fulfilled_distributions,
            'pending_distributions': pending_distributions,
            'evacuees': evacuees,
            'total_evacuees': total_evacuees
        })

    # Get all municipalities for filter dropdown
    municipalities = Municipality.objects.all()

    context = {
        'consolidated_data': consolidated_data,
        'municipalities': municipalities,
    }

    return render(request, 'admin/consolidated_table_view.html', context)


@login_required
def export_consolidated_pdf(request):
    """
    Generate a PDF report of the consolidated data table
    """
    # Check if user is admin
    if not request.user.is_staff:
        messages.error(request, "You do not have permission to access this page.")
        return redirect('dashboard')

    # Get all barangays with prefetched related data
    barangays = Barangay.objects.all().select_related('municipality')

    # Prepare consolidated data
    consolidated_data = []

    for barangay in barangays:
        # Get barangay captain
        captain = User.objects.filter(
            reporterprofile__barangay=barangay,
            reporterprofile__is_barangay_captain=True
        ).first()

        # Get evacuation centers in this barangay
        centers = EvacuationCenter.objects.filter(barangay=barangay)

        # Get incidents in this barangay
        incidents = IncidentReport.objects.filter(barangay=barangay)
        verified_incidents = incidents.filter(status='verified').count()
        pending_incidents = incidents.filter(status='pending').count()

        # Get distributions for incidents in this barangay
        distributions = IncidentDistribution.objects.filter(incident__in=incidents)
        fulfilled_distributions = distributions.filter(status='distributed').count()
        pending_distributions = distributions.filter(status__in=['pending', 'approved']).count()

        # Get evacuees from evacuation centers in this barangay
        center_ids = centers.values_list('id', flat=True)
        evacuees = Evacuee.objects.filter(evacuation_center__in=center_ids)
        active_evacuees = evacuees.filter(date_departed__isnull=True)

        # Calculate total evacuees (currently in centers)
        total_evacuees = active_evacuees.count()

        # Add to consolidated data
        consolidated_data.append({
            'barangay': barangay,
            'captain': captain,
            'evacuation_centers': centers,
            'incidents': incidents,
            'verified_incidents': verified_incidents,
            'pending_incidents': pending_incidents,
            'distributions': distributions,
            'fulfilled_distributions': fulfilled_distributions,
            'pending_distributions': pending_distributions,
            'evacuees': evacuees,
            'total_evacuees': total_evacuees
        })

    # Create a file-like buffer to receive PDF data
    buffer = io.BytesIO()

    # Import ReportLab components
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    from reportlab.lib.enums import TA_CENTER, TA_LEFT
    from django.conf import settings

    # Create the PDF object, using the buffer as its "file"
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(letter),
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )

    # Container for the 'Flowable' objects
    elements = []

    # Define styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading1'],
        fontSize=16,
        alignment=TA_CENTER,
        spaceAfter=12
    )

    subtitle_style = ParagraphStyle(
        'Subtitle',
        parent=styles['Normal'],
        fontSize=12,
        alignment=TA_CENTER,
        spaceAfter=12
    )

    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading2'],
        fontSize=12,
        alignment=TA_LEFT,
        spaceAfter=6
    )

    normal_style = styles["Normal"]

    # Add the logo
    logo_path = os.path.join(settings.BASE_DIR, 'static', 'logo', 'mdrrmc_logo.png')
    if os.path.exists(logo_path):
        logo = Image(logo_path)
        logo.drawHeight = 0.8 * inch
        logo.drawWidth = 0.8 * inch
        elements.append(logo)

    # Add title and date
    elements.append(Paragraph("Consolidated Barangay Data Report", title_style))
    elements.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y')}", subtitle_style))
    elements.append(Spacer(1, 0.2*inch))

    # Create table data
    data = [
        [
            'Barangay',
            'Municipality',
            'Barangay Captain',
            'Evacuation Centers',
            'Total Evacuees',
            'Incident Reports',
            'Distributions'
        ]
    ]

    # Add data rows
    for item in consolidated_data:
        barangay = item['barangay']
        captain_name = item['captain'].get_full_name() if item['captain'] else "Not assigned"

        # Format evacuation centers
        centers_text = ""
        for center in item['evacuation_centers']:
            status_text = center.get_status_display()
            centers_text += f"{center.name} ({status_text}: {center.current_occupancy}/{center.capacity})\n"

        if not centers_text:
            centers_text = "None"

        # Format incidents
        incidents_text = f"Total: {item['incidents'].count()}\n"
        incidents_text += f"Verified: {item['verified_incidents']}\n"
        incidents_text += f"Pending: {item['pending_incidents']}"

        # Format distributions
        distributions_text = f"Total: {item['distributions'].count()}\n"
        distributions_text += f"Fulfilled: {item['fulfilled_distributions']}\n"
        distributions_text += f"Pending: {item['pending_distributions']}"

        data.append([
            barangay.name,
            barangay.municipality.name,
            captain_name,
            centers_text,
            str(item['total_evacuees']),
            incidents_text,
            distributions_text
        ])

    # Create the table
    table = Table(data, repeatRows=1)

    # Add style to table
    table.setStyle(TableStyle([
        # Header style
        ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),

        # Row styles
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 8),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),

        # Alternating row colors
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),

        # Grid
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
        ('BOX', (0, 0), (-1, -1), 1, colors.black),

        # Column widths
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))

    # Add the table to elements
    elements.append(table)

    # Add summary information
    elements.append(Spacer(1, 0.3*inch))
    elements.append(Paragraph("Summary Information", header_style))

    # Calculate summary statistics
    total_barangays = len(consolidated_data)
    total_centers = sum(len(item['evacuation_centers']) for item in consolidated_data)
    total_evacuees = sum(item['total_evacuees'] for item in consolidated_data)
    total_incidents = sum(item['incidents'].count() for item in consolidated_data)
    total_distributions = sum(item['distributions'].count() for item in consolidated_data)

    # Create summary table
    summary_data = [
        ['Total Barangays', 'Total Evacuation Centers', 'Total Evacuees', 'Total Incidents', 'Total Distributions'],
        [str(total_barangays), str(total_centers), str(total_evacuees), str(total_incidents), str(total_distributions)]
    ]

    summary_table = Table(summary_data, repeatRows=1)
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.blue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
        ('BACKGROUND', (0, 1), (-1, 1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
    ]))

    elements.append(summary_table)

    # Add footer with page numbers
    def add_page_number(canvas, doc):
        canvas.saveState()
        canvas.setFont('Helvetica', 8)
        page_num = canvas.getPageNumber()
        text = f"Page {page_num}"
        canvas.drawRightString(doc.width + doc.rightMargin - 10, doc.bottomMargin - 20, text)
        canvas.restoreState()

    # Build the PDF
    doc.build(elements, onFirstPage=add_page_number, onLaterPages=add_page_number)

    # Get the value of the BytesIO buffer and write it to the response
    pdf = buffer.getvalue()
    buffer.close()

    # Create the HttpResponse object with the appropriate PDF headers
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="consolidated_barangay_report.pdf"'

    return response
