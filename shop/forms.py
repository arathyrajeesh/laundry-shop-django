from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone
from .models import Profile,Service,Branch,Order

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
