from django.contrib import admin
from .models import Profile, Order, LaundryShop,Service,Branch

# Register your models here.

@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'full_name', 'phone']
    search_fields = ['user__username', 'full_name', 'phone']


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'shop', 'cloth_status', 'amount', 'created_at']
    list_filter = ['cloth_status', 'created_at']
    search_fields = ['user__username', 'user__email', 'shop__name']
    readonly_fields = ['created_at']
    list_editable = ['cloth_status']


@admin.register(LaundryShop)
class LaundryShopAdmin(admin.ModelAdmin):
    list_display = ['name', 'address', 'phone', 'is_open']
    list_filter = ['is_open']
    search_fields = ['name', 'address', 'phone']
    list_editable = ['is_open']


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'price', 'created_at')
    list_filter = ('branch__shop',)

@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'shop', 'phone')
    list_filter = ('shop',)
