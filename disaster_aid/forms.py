from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import (
    ReporterProfile, IncidentReport, DisasterType, IncidentDistribution,
    DistributionType, Inventory, Municipality, Barangay
)

# Common form field styling
INPUT_CLASSES = 'w-full px-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent'
LOGIN_INPUT_CLASSES = 'w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-primary focus:border-transparent input-field'

class LoginForm(AuthenticationForm):
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': LOGIN_INPUT_CLASSES,
                'placeholder': 'Enter your username',
            }
        )
    )
    password = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': LOGIN_INPUT_CLASSES,
                'placeholder': 'Enter your password',
            }
        )
    )

class RegisterForm(UserCreationForm):
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'First Name',
            }
        )
    )
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Last Name',
            }
        )
    )
    email = forms.EmailField(
        max_length=254,
        required=True,
        widget=forms.EmailInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Email Address',
            }
        )
    )
    username = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Username',
            }
        )
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Password',
            }
        )
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Confirm Password',
            }
        )
    )
    profile_image = forms.ImageField(
        required=True,
        widget=forms.FileInput(
            attrs={
                'class': INPUT_CLASSES,
                'accept': 'image/*',
            }
        )
    )

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']

        if commit:
            user.save()
            # Create the user profile with the profile image
            profile_image = self.cleaned_data.get('profile_image')
            ReporterProfile.objects.create(
                user=user,
                profile_image=profile_image
            )

        return user

class IncidentReportForm(forms.ModelForm):
    title = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Incident Title',
            }
        )
    )
    description = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Detailed description of the incident',
                'rows': 5,
            }
        )
    )
    # Keep the location field for backward compatibility but make it optional
    location = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Additional location details (optional)',
            }
        )
    )
    # Add barangay field
    barangay = forms.ModelChoiceField(
        queryset=Barangay.objects.filter(municipality__name='Tambulig').order_by('name'),
        empty_label="Select Barangay",
        widget=forms.Select(
            attrs={
                'class': INPUT_CLASSES,
            }
        )
    )
    disaster_type = forms.ModelChoiceField(
        queryset=DisasterType.objects.all(),
        empty_label="Select Disaster Type",
        widget=forms.Select(
            attrs={
                'class': INPUT_CLASSES,
            }
        )
    )

    # Resource needs fields
    needs_resources = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(
            attrs={
                'class': 'h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded',
            }
        )
    )

    # Photo upload fields
    photo_1 = forms.ImageField(
        required=False,
        widget=forms.FileInput(
            attrs={
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
                'accept': 'image/*',
            }
        )
    )
    photo_2 = forms.ImageField(
        required=False,
        widget=forms.FileInput(
            attrs={
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
                'accept': 'image/*',
            }
        )
    )
    photo_3 = forms.ImageField(
        required=False,
        widget=forms.FileInput(
            attrs={
                'class': 'block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100',
                'accept': 'image/*',
            }
        )
    )

    class Meta:
        model = IncidentReport
        fields = ['title', 'description', 'barangay', 'location', 'disaster_type', 'needs_resources', 'photo_1', 'photo_2', 'photo_3']

class DistributionRequestForm(forms.ModelForm):
    distribution_type = forms.ModelChoiceField(
        queryset=DistributionType.objects.all(),
        empty_label="Select Resource Type",
        widget=forms.Select(
            attrs={
                'class': INPUT_CLASSES,
            }
        )
    )
    quantity_requested = forms.IntegerField(
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Quantity Needed',
            }
        )
    )

    class Meta:
        model = IncidentDistribution
        fields = ['distribution_type', 'quantity_requested']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Only show distribution types that have inventory
        self.fields['distribution_type'].queryset = DistributionType.objects.filter(
            inventory__quantity_available__gt=0
        )

class ResourceRequestFormSet(forms.BaseFormSet):
    def clean(self):
        """
        Validate that at least one resource request is filled out if needs_resources is checked
        """
        if any(self.errors):
            return

        if not self.forms[0].cleaned_data:
            raise forms.ValidationError("At least one resource request must be filled out.")

        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE', False):
                # Check that both fields are filled
                if not form.cleaned_data.get('distribution_type') or not form.cleaned_data.get('quantity_requested'):
                    raise forms.ValidationError("Both resource type and quantity must be provided.")

class InventoryForm(forms.ModelForm):
    quantity_available = forms.IntegerField(
        min_value=0,
        widget=forms.NumberInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Available Quantity',
            }
        )
    )

    class Meta:
        model = Inventory
        fields = ['quantity_available']


class DenyIncidentForm(forms.Form):
    denial_reason = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Please provide a reason for denying this incident report',
                'rows': 3,
            }
        ),
        required=True,
        help_text='This reason will be shared with the reporter to explain why their incident was denied.'
    )
