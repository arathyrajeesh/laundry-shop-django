from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from cloudinary.models import CloudinaryField

class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    full_name = models.CharField(max_length=100, blank=True)
    phone = models.CharField(max_length=15, blank=True)
    profile_image = CloudinaryField('image', blank=True, null=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    email_verified = models.BooleanField(default=False)
    notifications_enabled = models.BooleanField(default=True)
    login_email_sent = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.username}'s profile"

class LaundryShop(models.Model):
    name = models.CharField(max_length=100, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128, blank=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=15, blank=True)
    city = models.CharField(max_length=100, blank=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    is_approved = models.BooleanField(default=False)
    is_open = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)
    
    razorpay_account_id = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Razorpay Account ID for marketplace payments"
    )
    
    # Bank Details
    bank_account_holder_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Account holder name as per bank records"
    )
    bank_account_number = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        help_text="Bank account number"
    )
    bank_ifsc_code = models.CharField(
        max_length=11,
        blank=True,
        null=True,
        help_text="IFSC code (e.g., HDFC0001234)"
    )
    bank_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Bank name (e.g., HDFC Bank, SBI)"
    )
    bank_branch = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        help_text="Bank branch name"
    )
    bank_account_type = models.CharField(
        max_length=20,
        choices=[
            ('Savings', 'Savings'),
            ('Current', 'Current'),
        ],
        blank=True,
        null=True,
        help_text="Type of bank account"
    )
    
    def set_password(self, raw_password):
        from django.contrib.auth.hashers import make_password
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        from django.contrib.auth.hashers import check_password
        return check_password(raw_password, self.password)

    def __str__(self):
        return self.name

class Branch(models.Model):
    shop = models.ForeignKey(LaundryShop, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=100)
    address = models.TextField()
    phone = models.CharField(max_length=15, blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('shop', 'name')

    def __str__(self):
        return f"{self.shop.name} - {self.name}"

class Service(models.Model):
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    cloths = models.ManyToManyField('Cloth', blank=True, related_name='services')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('branch', 'name')

    def __str__(self):
        return f"{self.branch.name} - {self.name}"

class Cloth(models.Model):
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return self.name

class ServiceClothPrice(models.Model):
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='cloth_prices')
    cloth = models.ForeignKey(Cloth, on_delete=models.CASCADE, related_name='service_prices')
    price = models.DecimalField(max_digits=10, decimal_places=2, help_text="Price for this cloth type in this service")

    class Meta:
        unique_together = ('service', 'cloth')

    def __str__(self):
        return f"{self.service.name} - {self.cloth.name}: ₹{self.price}"

class Order(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Washing', 'Washing'),
        ('Drying', 'Drying'),
        ('Ironing', 'Ironing'),
        ('Ready', 'Ready for Pickup'),
        ('Completed', 'Completed'),
    ]

    PAYMENT_CHOICES = [
        ('Pending', 'Pending'),
        ('Completed', 'Completed'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shop = models.ForeignKey(LaundryShop, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE, blank=True, null=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    cloth_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pending')
    payment_status = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='Pending')
    pickup_date = models.DateTimeField(blank=True, null=True)
    delivery_date = models.DateTimeField(blank=True, null=True)
    delivery_name = models.CharField(max_length=100, blank=True)
    delivery_address = models.TextField(blank=True)
    delivery_phone = models.CharField(max_length=15, blank=True)
    special_instructions = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    delay_notified = models.BooleanField(default=False)
    thank_you_sent = models.BooleanField(default=False)
    
    # Payment tracking fields for marketplace payments
    platform_commission = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Platform commission amount")
    shop_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, help_text="Amount to be transferred to shop")
    razorpay_payment_id = models.CharField(max_length=100, blank=True, null=True, help_text="Razorpay payment ID")
    razorpay_order_id = models.CharField(max_length=100, blank=True, null=True, help_text="Razorpay order ID")
    transfer_id = models.CharField(max_length=100, blank=True, null=True, help_text="Razorpay transfer ID to shop")
    transfer_status = models.CharField(max_length=50, default='Pending', help_text="Status of transfer to shop")
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.username}"

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50)
    icon = models.CharField(max_length=50, default='fas fa-bell')
    color = models.CharField(max_length=20, default='#3498db')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.user.username} - {self.title}"

class ShopRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    shop = models.ForeignKey(LaundryShop, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'shop')

    def __str__(self):
        return f"{self.user.username} rated {self.shop.name}: {self.rating}"

class ServiceRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'service')

    def __str__(self):
        return f"{self.user.username} rated {self.service.name}: {self.rating}"

class BranchRating(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    branch = models.ForeignKey(Branch, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField(blank=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('user', 'branch')

    def __str__(self):
        return f"{self.user.username} rated {self.branch.name}: {self.rating}"

class EmailVerificationToken(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Token for {self.user.username}"

class ShopPasswordResetToken(models.Model):
    shop = models.ForeignKey(LaundryShop, on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(default=timezone.now)

    def is_expired(self):
        return timezone.now() > self.created_at + timezone.timedelta(hours=1)

class NewsletterSubscriber(models.Model):
    email = models.EmailField(unique=True)
    subscribed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.email

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='order_items')
    service = models.ForeignKey(Service, on_delete=models.CASCADE)
    cloth = models.ForeignKey(Cloth, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.order.id} - {self.service.name} - {self.cloth.name} x{self.quantity}"
