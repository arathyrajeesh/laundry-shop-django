from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone
from .models import Profile,Service,Branch,Order,LaundryShop

class CustomPasswordChangeForm(PasswordChangeForm):
    send_email = forms.BooleanField(
        required=False,
        initial=True,
        label="Send confirmation email",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

class ProfileForm(forms.ModelForm):
    class Meta:
        model = Profile
        fields = ['full_name', 'phone', 'profile_image', 'city']


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name', 'price']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Service name'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Price (optional)'}),
        }

class BranchForm(forms.ModelForm):
    class Meta:
        model = Branch
        fields = ['name', 'address', 'phone']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Branch name'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact phone (optional)'}),
        }

class UserDetailsForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['pickup_date', 'delivery_date', 'delivery_name', 'delivery_address', 'delivery_phone', 'special_instructions']
        widgets = {
            'pickup_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local', 'min': timezone.now().strftime('%Y-%m-%dT%H:%M')}),
            'delivery_date': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local', 'min': timezone.now().strftime('%Y-%m-%dT%H:%M')}),
            'delivery_name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Full name for delivery'}),
            'delivery_address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full delivery address'}),
            'delivery_phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact phone number'}),
            'special_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 2, 'placeholder': 'Special instructions (optional)'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['pickup_date'].required = True
        self.fields['delivery_date'].required = True
        self.fields['delivery_name'].required = True
        self.fields['delivery_address'].required = True
        self.fields['delivery_phone'].required = True

    def clean_pickup_date(self):
        pickup_date = self.cleaned_data.get('pickup_date')
        if pickup_date and pickup_date < timezone.now():
            raise forms.ValidationError("Pickup date cannot be in the past.")
        return pickup_date

    def clean_delivery_date(self):
        delivery_date = self.cleaned_data.get('delivery_date')
        if delivery_date and delivery_date < timezone.now():
            raise forms.ValidationError("Delivery date cannot be in the past.")
        return delivery_date

    def clean(self):
        cleaned_data = super().clean()
        pickup_date = cleaned_data.get('pickup_date')
        delivery_date = cleaned_data.get('delivery_date')

        if pickup_date and delivery_date and pickup_date == delivery_date:
            self.add_error('delivery_date', "Pickup date and delivery date cannot be the same.")

        return cleaned_data

class LaundryShopForm(forms.ModelForm):
    class Meta:
        model = LaundryShop
        fields = ['name', 'email', 'address', 'phone', 'city', 'latitude', 'longitude', 'is_approved', 'is_open', 'razorpay_account_id']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Shop name'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email address'}),
            'address': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Full address'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Contact phone'}),
            'city': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'City'}),
            'latitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Latitude', 'step': 'any'}),
            'longitude': forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Longitude', 'step': 'any'}),
            'is_approved': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'is_open': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'razorpay_account_id': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Razorpay Account ID (for marketplace payments)',
                'help_text': 'Enter the Razorpay account ID for this shop to enable direct payments'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['razorpay_account_id'].required = False
        self.fields['razorpay_account_id'].help_text = 'Razorpay Connect Account ID. Leave empty if shop will receive payments manually.'


class ShopBankDetailsForm(forms.ModelForm):
    """Form for shops to manage their bank details."""
    class Meta:
        model = LaundryShop
        fields = [
            'bank_account_holder_name',
            'bank_account_number',
            'bank_ifsc_code',
            'bank_name',
            'bank_branch',
            'bank_account_type',
        ]
        widgets = {
            'bank_account_holder_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Account holder name (as per bank records)'
            }),
            'bank_account_number': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank account number',
                'type': 'text'
            }),
            'bank_ifsc_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'IFSC Code (e.g., HDFC0001234)',
                'style': 'text-transform: uppercase;'
            }),
            'bank_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bank name (e.g., HDFC Bank, SBI)'
            }),
            'bank_branch': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Branch name'
            }),
            'bank_account_type': forms.Select(attrs={
                'class': 'form-control'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make all fields optional
        for field in self.fields:
            self.fields[field].required = False
    
    def clean_bank_ifsc_code(self):
        """Validate IFSC code format."""
        ifsc = self.cleaned_data.get('bank_ifsc_code')
        if ifsc:
            ifsc = ifsc.upper().strip()
            # IFSC code should be 11 characters: 4 letters + 0 + 6 alphanumeric
            if len(ifsc) != 11:
                raise forms.ValidationError("IFSC code must be 11 characters long (e.g., HDFC0001234)")
            if not ifsc[:4].isalpha():
                raise forms.ValidationError("IFSC code must start with 4 letters")
            if ifsc[4] != '0':
                raise forms.ValidationError("IFSC code must have '0' at position 5")
        return ifsc
    
    def clean_bank_account_number(self):
        """Validate bank account number."""
        account_number = self.cleaned_data.get('bank_account_number')
        if account_number:
            # Remove spaces and hyphens
            account_number = account_number.replace(' ', '').replace('-', '')
            # Account number should be numeric and between 9-18 digits
            if not account_number.isdigit():
                raise forms.ValidationError("Account number must contain only digits")
            if len(account_number) < 9 or len(account_number) > 18:
                raise forms.ValidationError("Account number must be between 9 and 18 digits")
        return account_number
