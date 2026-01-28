from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone
from .models import Profile,Service,Branch,Order,LaundryShop,ServiceClothPrice,Cloth

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
        fields = ["full_name", "phone", "city", "profile_image"]
        widgets = {
            "city": forms.TextInput(attrs={
                "id": "cityInput",
                "class": "form-input"
            }),
            "full_name": forms.TextInput(attrs={"class": "form-input"}),
            "phone": forms.TextInput(attrs={"class": "form-input"}),
        }


class ServiceForm(forms.ModelForm):
    class Meta:
        model = Service
        fields = ['name']
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Service name'}),
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

from django import forms
from django.utils import timezone
from .models import Order
import re

from django import forms
from django.utils import timezone
from .models import Order

from django import forms
from django.utils import timezone
from .models import Order

from django import forms
from django.utils import timezone
from .models import Order

class UserDetailsForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['pickup_date', 'delivery_date', 'delivery_name', 'delivery_address', 'delivery_phone', 'special_instructions']
        widgets = {
            'pickup_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'input-styled'}),
            'delivery_date': forms.DateTimeInput(attrs={'type': 'datetime-local', 'class': 'input-styled'}),
            'delivery_phone': forms.TextInput(attrs={
                'placeholder': '10-digit mobile number',
                'inputmode': 'numeric',
                'class': 'input-styled',
                'oninput': "this.value = this.value.replace(/[^0-9]/g, '').substring(0, 10)"
            }),
            'delivery_name': forms.TextInput(attrs={'placeholder': 'Full name', 'class': 'input-styled'}),
            'delivery_address': forms.Textarea(attrs={'placeholder': 'Full address', 'class': 'input-styled', 'rows': 3}),
            'special_instructions': forms.Textarea(attrs={'placeholder': 'Optional instructions', 'class': 'input-styled', 'rows': 2}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 🚩 Mark these fields as mandatory
        mandatory_fields = ['pickup_date', 'delivery_date', 'delivery_name', 'delivery_address', 'delivery_phone']
        for field in mandatory_fields:
            self.fields[field].required = True

    def clean_delivery_phone(self):
        phone = self.cleaned_data.get('delivery_phone')
        # Catch alphabet or special characters
        if not phone.isdigit():
            raise forms.ValidationError("Error: Only numbers are allowed in the phone section.")
        # Catch 9 digits or less
        if len(phone) != 10:
            raise forms.ValidationError(f"Error: Exactly 10 digits required. You typed {len(phone)}.")
        return phone

    def clean(self):
        cleaned_data = super().clean()
        pickup = cleaned_data.get('pickup_date')
        delivery = cleaned_data.get('delivery_date')

        if pickup and delivery:
            if pickup < timezone.now():
                self.add_error('pickup_date', "Pickup date cannot be in the past.")
            if delivery <= pickup:
                self.add_error('delivery_date', "Delivery must be scheduled after the pickup time.")
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
    """Form for shops to manage their Razorpay details."""
    class Meta:
        model = LaundryShop
        fields = [
            'razorpay_key_id',
            'razorpay_key_secret',
        ]
        widgets = {
            'razorpay_key_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Razorpay Key ID (e.g., rzp_test_...)',
            }),
            'razorpay_key_secret': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Razorpay Key Secret',
                'type': 'password'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Make Razorpay fields required
        self.fields['razorpay_key_id'].required = True
        self.fields['razorpay_key_secret'].required = True
    
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
