from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.models import User
from .models import (
    ReporterProfile, IncidentReport, DisasterType, IncidentDistribution,
    DistributionType, Inventory, Municipality, Barangay, DisasterAlert,
    EvacuationCenter, Evacuee
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
        required=False,  # Not required since we'll generate it
        widget=forms.EmailInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Email Address',
                'style': 'display: none;',  # Hide the original email field
            }
        )
    )
    barangay = forms.ModelChoiceField(
        queryset=Barangay.objects.filter(municipality__name='Tambulig').order_by('name'),
        empty_label="-- Select Your Barangay --",
        required=True,
        widget=forms.Select(
            attrs={
                'class': INPUT_CLASSES + ' border-2 border-blue-300',
                'style': 'background-color: #f0f9ff;',  # Light blue background
            }
        )
    )

    def __init__(self, *args, **kwargs):
        print("DEBUG - RegisterForm.__init__ called")
        super().__init__(*args, **kwargs)
        # Make sure the barangay field is required
        self.fields['barangay'].required = True
        # Make sure the email field is not required in the form (we'll generate it)
        self.fields['email'].required = False
        print(f"DEBUG - Form initialized with fields: {self.fields.keys()}")

        # Check if data was provided
        if args and args[0]:
            print(f"DEBUG - Form initialized with data: {args[0]}")
            if 'barangay' in args[0]:
                print(f"DEBUG - Barangay in POST data: {args[0]['barangay']}")

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

    # No checkbox needed - all registered users with a barangay are automatically barangay captains

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password1', 'password2')

    # We need to handle the barangay field separately since it's not part of the User model

    def clean(self):
        cleaned_data = super().clean()
        # Print debug info
        print(f"DEBUG - clean method called, cleaned_data: {cleaned_data}")

        # Only validate barangay if this is a POST request (form submission)
        if self.is_bound:
            # Validate that barangay is selected
            barangay = cleaned_data.get('barangay')
            if not barangay:
                print("DEBUG - No barangay selected, raising validation error")
                from django.core.exceptions import ValidationError
                raise ValidationError({
                    'barangay': 'Please select your barangay address. This is required for registration.'
                })

            # Generate a placeholder email using the barangay name and username for uniqueness
            username = cleaned_data.get('username', '').lower()
            barangay_name = barangay.name.lower().replace(' ', '_')
            email = f"{username}_{barangay_name}@example.com"
            cleaned_data['email'] = email
            print(f"DEBUG - Generated email: {email} for barangay: {barangay.name}")

        return cleaned_data

    def clean_barangay(self):
        """Specific validation for the barangay field"""
        # Only validate if the form is bound (POST request)
        if not self.is_bound:
            return None

        # Get the barangay value
        barangay = self.cleaned_data.get('barangay')
        print(f"DEBUG - clean_barangay called with value: {barangay}")

        # Validate the barangay field
        if not barangay and 'barangay' in self.data:
            print("DEBUG - Barangay field is required")
            from django.core.exceptions import ValidationError
            raise ValidationError("Please select your barangay from the dropdown. This information is required for registration.")

        return barangay

    def save(self, commit=True):
        print("DEBUG - save method called")
        try:
            # Get the barangay before saving the user
            barangay = self.cleaned_data.get('barangay')
            print(f"DEBUG - Barangay from cleaned_data: {barangay}")

            if not barangay:
                print("DEBUG - No barangay selected, cannot proceed")
                raise ValueError("Please select your barangay address")

            # Generate a placeholder email using the barangay name
            email = f"{barangay.name.lower().replace(' ', '_')}@example.com"
            # Make sure email is in cleaned_data
            self.cleaned_data['email'] = email
            print(f"DEBUG - Generated email: {email}")

            # Save the user
            user = super().save(commit=False)
            print(f"DEBUG - User object created: {user.username}")

            user.first_name = self.cleaned_data.get('first_name', '')
            user.last_name = self.cleaned_data.get('last_name', '')
            # Set the email directly on the user object
            user.email = email

            print(f"DEBUG - User object before save: {user.username}, {user.email}, {user.first_name}, {user.last_name}")

            if commit:
                print("DEBUG - Saving user to database")
                user.save()
                print(f"DEBUG - User saved with ID: {user.id}")

                # Create the user profile with the profile image and barangay
                profile_image = self.cleaned_data.get('profile_image')

                print(f"DEBUG - Creating profile with barangay: {barangay}")

                # All registered users with a barangay are automatically barangay captains

                # Create the profile directly
                profile = ReporterProfile.objects.create(
                    user=user,
                    profile_image=profile_image,
                    barangay=barangay,
                    is_barangay_captain=True  # Automatically set as barangay captain
                )
                print(f"DEBUG - Profile created with ID: {profile.id}")

            return user
        except Exception as e:
            import traceback
            print(f"DEBUG - Exception in save method: {str(e)}")
            print(traceback.format_exc())
            raise

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
    incident_datetime = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(
            attrs={
                'class': INPUT_CLASSES,
                'type': 'datetime-local',
            }
        ),
        help_text='When did the incident occur? Leave blank if reporting in real-time.'
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
                'id': 'id_disaster_type_select',
            }
        )
    )

    other_disaster_type = forms.CharField(
        required=False,
        widget=forms.TextInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Please specify the disaster type',
                'id': 'id_other_disaster_type',
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
        fields = ['title', 'description', 'barangay', 'location', 'disaster_type', 'other_disaster_type', 'incident_datetime', 'needs_resources', 'photo_1', 'photo_2', 'photo_3']

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
                'placeholder': 'Please provide a reason for disapproving this incident report',
                'rows': 3,
            }
        ),
        required=True,
        help_text='This reason will be shared with the reporter to explain why their incident was disapproved.'
    )


class DisasterAlertForm(forms.ModelForm):
    title = forms.CharField(
        widget=forms.TextInput(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Alert Title',
            }
        )
    )
    message = forms.CharField(
        widget=forms.Textarea(
            attrs={
                'class': INPUT_CLASSES,
                'placeholder': 'Detailed alert message with instructions',
                'rows': 4,
            }
        )
    )
    severity = forms.ChoiceField(
        choices=DisasterAlert.SEVERITY_CHOICES,
        widget=forms.Select(
            attrs={
                'class': INPUT_CLASSES,
            }
        )
    )

    class Meta:
        model = DisasterAlert
        fields = ['title', 'message', 'severity']


class EvacuationCenterForm(forms.ModelForm):
    class Meta:
        model = EvacuationCenter
        fields = ['name', 'barangay', 'address', 'capacity', 'facilities', 'contact_info', 'notes']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Evacuation Center Name'}),
            'barangay': forms.Select(attrs={'class': INPUT_CLASSES}),
            'address': forms.Textarea(attrs={'class': INPUT_CLASSES, 'rows': 3, 'placeholder': 'Detailed address of the evacuation center'}),
            'capacity': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'min': 1, 'placeholder': 'Maximum number of people'}),
            'facilities': forms.Textarea(attrs={'class': INPUT_CLASSES, 'rows': 3,
                                               'placeholder': 'e.g., 5 toilets, kitchen, medical area, etc.'}),
            'contact_info': forms.TextInput(attrs={'class': INPUT_CLASSES,
                                                  'placeholder': 'Phone number or contact person'}),
            'notes': forms.Textarea(attrs={'class': INPUT_CLASSES, 'rows': 3, 'placeholder': 'Additional notes'}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)

        # If the user is a barangay captain, pre-select their barangay and make it read-only
        if user and not user.is_superuser:
            try:
                profile = user.reporterprofile
                if profile.is_barangay_captain and profile.barangay:
                    self.fields['barangay'].initial = profile.barangay
                    self.fields['barangay'].widget.attrs['disabled'] = 'disabled'
                    self.fields['barangay'].required = False
            except:
                pass

    def clean_barangay(self):
        # If the barangay field is disabled in the form, it won't be in cleaned_data
        # So we need to get it from the initial data
        if 'barangay' not in self.cleaned_data and self.initial.get('barangay'):
            return self.initial.get('barangay')
        return self.cleaned_data.get('barangay')


class EvacueeForm(forms.ModelForm):
    class Meta:
        model = Evacuee
        fields = ['name', 'age', 'gender', 'head_of_family', 'family_name',
                 'special_needs', 'contact_number', 'evacuation_center']
        widgets = {
            'name': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Full Name'}),
            'age': forms.NumberInput(attrs={'class': INPUT_CLASSES, 'min': 0, 'placeholder': 'Age'}),
            'gender': forms.Select(attrs={'class': INPUT_CLASSES}),
            'head_of_family': forms.CheckboxInput(attrs={'class': 'h-4 w-4 text-primary focus:ring-primary border-gray-300 rounded'}),
            'family_name': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Family Name (for grouping)'}),
            'special_needs': forms.Textarea(attrs={'class': INPUT_CLASSES, 'rows': 2, 'placeholder': 'Any special needs or medical conditions'}),
            'contact_number': forms.TextInput(attrs={'class': INPUT_CLASSES, 'placeholder': 'Contact Number'}),
            'evacuation_center': forms.Select(attrs={'class': INPUT_CLASSES}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        center_id = kwargs.pop('center_id', None)
        super().__init__(*args, **kwargs)

        # If a specific evacuation center is provided, pre-select it and make it read-only
        if center_id:
            try:
                center = EvacuationCenter.objects.get(id=center_id)
                self.fields['evacuation_center'].initial = center
                self.fields['evacuation_center'].widget.attrs['disabled'] = 'disabled'
                self.fields['evacuation_center'].required = False
            except:
                pass
        # If the user is a barangay captain, limit evacuation centers to their barangay
        elif user and not user.is_superuser:
            try:
                profile = user.reporterprofile
                if profile.is_barangay_captain and profile.barangay:
                    self.fields['evacuation_center'].queryset = EvacuationCenter.objects.filter(
                        barangay=profile.barangay
                    )
            except:
                pass

    def clean_evacuation_center(self):
        # If the evacuation_center field is disabled in the form, it won't be in cleaned_data
        # So we need to get it from the initial data
        if 'evacuation_center' not in self.cleaned_data and self.initial.get('evacuation_center'):
            return self.initial.get('evacuation_center')
        return self.cleaned_data.get('evacuation_center')
