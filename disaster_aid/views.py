from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, authenticate, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Sum, Count
from django.http import JsonResponse
from django.core.paginator import Paginator
from .forms import (
    LoginForm, RegisterForm, IncidentReportForm,
    DistributionRequestForm, InventoryForm, DenyIncidentForm
)
from .models import (
    IncidentReport, DisasterType, DistributionType,
    Inventory, IncidentDistribution, UserNotification
)

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
        form = RegisterForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, f"Account created for {user.username}!")
            return redirect('home')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = RegisterForm()

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

    if request.method == 'POST':
        form = IncidentReportForm(request.POST, request.FILES)
        if form.is_valid():
            # Save the incident report
            incident = form.save(commit=False)
            incident.reporter = request.user
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

                    if not resource_type_id or not quantity:
                        # No more resources to process
                        if resource_count == 1:
                            # No resources were specified
                            messages.warning(request, "You indicated resource needs but didn't specify any resources.")
                        break

                    try:
                        resource_type = DistributionType.objects.get(id=resource_type_id)
                        quantity = int(quantity)

                        if quantity <= 0:
                            messages.warning(request, f"Invalid quantity for {resource_type.name}. Must be greater than 0.")
                            continue

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
    fulfilled_count = distributions.filter(is_fulfilled=True).count()
    pending_count = total_count - fulfilled_count

    # Get inventory information for each distribution type
    inventories = {inv.item_id: inv.quantity_available for inv in Inventory.objects.all()}

    # Filter by status if provided
    status = request.GET.get('status')
    if status == 'fulfilled':
        distributions = distributions.filter(is_fulfilled=True)
    elif status == 'pending':
        distributions = distributions.filter(is_fulfilled=False)

    # Paginate distributions
    paginator = Paginator(distributions, 10)  # Show 10 distributions per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'status': status,
        'total_count': total_count,
        'fulfilled_count': fulfilled_count,
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
        messages.success(request, f"Distribution of {distribution.quantity_approved} {distribution.distribution_type.name} approved successfully.")
    except ValueError as e:
        messages.error(request, str(e))

    return redirect('distribution_list')

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
