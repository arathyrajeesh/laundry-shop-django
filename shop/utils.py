# utils.py

from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from .models import Order, Notification

def notify_delayed_orders():
    now = timezone.now()

    delayed_orders = Order.objects.filter(
        delivery_date__isnull=False,
        delivery_date__lt=now,
        cloth_status__in=['Pending', 'Washing', 'Drying', 'Ironing'],
        delay_notified=False
    )

    for order in delayed_orders:
        user = order.user

        # ---------------- EMAIL ----------------
        subject = f"Order #{order.id} Delivery Delayed | Shine & Bright"
        message = f"""
Hi {user.get_full_name() or user.username},

We sincerely apologize for the delay in delivering your laundry order.

Order Details:
• Order ID: #{order.id}
• Shop: {order.shop.name}
• Expected Delivery: {order.delivery_date.strftime('%d %b %Y, %I:%M %p')}
• Current Status: {order.cloth_status}

Our team is actively working on your order and it will be delivered shortly.

Thank you for your patience.

— Shine & Bright Team 🧺✨
"""

        send_mail(
            subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=True
        )

        # ---------------- NOTIFICATION ----------------
        Notification.objects.create(
            user=user,
            title=f"Order #{order.id} Delayed",
            message="Your laundry delivery has been delayed. We apologize for the inconvenience.",
            notification_type="delay",
            icon="fas fa-clock",
            color="#e74c3c"
        )

        # ---------------- MARK AS SENT ----------------
        order.delay_notified = True
        order.save()
