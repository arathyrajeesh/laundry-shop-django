from django.contrib import admin
from .models import (
    Profile, LaundryShop, Branch, Service, Cloth,
    ServiceClothPrice, BranchCloth,
    Order, OrderItem,
    Notification,
    ShopRating, ServiceRating, BranchRating,
    EmailVerificationToken, ShopPasswordResetToken,
    NewsletterSubscriber
)

# -----------------------------
# PROFILE
# -----------------------------
@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone', 'city', 'email_verified')
    search_fields = ('user__username', 'full_name', 'phone')
    list_filter = ('email_verified', 'city')


# -----------------------------
# LAUNDRY SHOP
# -----------------------------
@admin.register(LaundryShop)
class LaundryShopAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'city', 'is_approved', 'is_open')
    list_filter = ('is_approved', 'city')
    search_fields = ('name', 'email', 'phone')
    readonly_fields = ('is_open', 'created_at')

    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'email', 'password', 'phone', 'address', 'city')
        }),
        ('Approval & Status', {
            'fields': ('is_approved', 'is_open')
        }),
        ('Razorpay Details', {
            'fields': (
                'razorpay_account_id',
                'razorpay_key_id',
                'razorpay_key_secret'
            ),
            'classes': ('collapse',)
        }),
        ('Bank Details', {
            'fields': (
                'bank_account_holder_name',
                'bank_account_number',
                'bank_ifsc_code',
                'bank_name',
                'bank_branch',
                'bank_account_type'
            ),
            'classes': ('collapse',)
        }),
    )


# -----------------------------
# BRANCH
# -----------------------------
@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ('name', 'shop', 'phone', 'created_at')
    list_filter = ('shop',)
    search_fields = ('name', 'shop__name')


# -----------------------------
# SERVICE
# -----------------------------
@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'branch', 'get_shop', 'price', 'created_at')
    list_filter = ('branch__shop',)
    search_fields = ('name', 'branch__name')

    def get_shop(self, obj):
        return obj.branch.shop.name
    get_shop.short_description = 'Shop'


# -----------------------------
# CLOTH
# -----------------------------
@admin.register(Cloth)
class ClothAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at')
    search_fields = ('name',)


# -----------------------------
# SERVICE–CLOTH PRICE
# -----------------------------
@admin.register(ServiceClothPrice)
class ServiceClothPriceAdmin(admin.ModelAdmin):
    list_display = ('service', 'cloth', 'price')
    list_filter = ('service', 'cloth')
    search_fields = ('service__name', 'cloth__name')


# -----------------------------
# BRANCH–CLOTH AVAILABILITY
# -----------------------------
@admin.register(BranchCloth)
class BranchClothAdmin(admin.ModelAdmin):
    list_display = ('branch', 'cloth')
    list_filter = ('branch', 'cloth')


# -----------------------------
# ORDER ITEMS INLINE
# -----------------------------
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0


# -----------------------------
# ORDER
# -----------------------------
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'shop', 'branch',
        'cloth_status', 'payment_status',
        'amount', 'created_at'
    )
    list_filter = (
        'cloth_status', 'payment_status',
        'created_at', 'shop'
    )
    search_fields = (
        'id', 'user__username',
        'user__email', 'shop__name'
    )
    readonly_fields = (
        'created_at',
        'razorpay_payment_id',
        'razorpay_order_id'
    )
    list_editable = ('cloth_status',)
    inlines = [OrderItemInline]


# -----------------------------
# NOTIFICATIONS
# -----------------------------
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('user__username', 'title')


# -----------------------------
# RATINGS
# -----------------------------
@admin.register(ShopRating)
class ShopRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'shop', 'rating', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('user__username', 'shop__name')


@admin.register(ServiceRating)
class ServiceRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'service', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('user__username', 'service__name')


@admin.register(BranchRating)
class BranchRatingAdmin(admin.ModelAdmin):
    list_display = ('user', 'branch', 'rating', 'created_at')
    list_filter = ('rating',)
    search_fields = ('user__username', 'branch__name')


# -----------------------------
# TOKENS & NEWSLETTER
# -----------------------------
@admin.register(EmailVerificationToken)
class EmailVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ('user', 'token', 'expires_at')
    search_fields = ('user__username',)


@admin.register(ShopPasswordResetToken)
class ShopPasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = ('shop', 'token', 'created_at')
    search_fields = ('shop__name',)


@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ('email', 'subscribed_at')
    search_fields = ('email',)
