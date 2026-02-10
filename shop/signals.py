from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth.models import User

from .models import Order, Profile


@receiver(post_save, sender=Order)
def send_thank_you_email(sender, instance, created, **kwargs):
    # IMPORTANT: skip signals during loaddata
    if kwargs.get("raw", False):
        return

    # If field doesn't exist, safely skip
    if not hasattr(instance, "thank_you_sent"):
        return

    if (
        instance.cloth_status == "Completed"
        and instance.payment_status == "Completed"
        and not instance.thank_you_sent
    ):
        user = instance.user

        subject = "Thank You for Choosing Shine & Bright 🧺✨"

        message = f"""
Hi {user.get_full_name() or user.username},

Thank you for choosing Shine & Bright Laundry Services! 🙏

We’re happy to inform you that your order has been successfully completed.

🧾 Order Details:
• Order ID: #{instance.id}
• Shop: {instance.shop.name}
• Amount Paid: ₹{instance.amount}
• Status: Completed

We truly appreciate your trust in us.
You can rate your experience and reorder anytime from your dashboard.

Looking forward to serving you again!

Warm regards,
Shine & Bright Team
🧺✨
"""

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[user.email],
            fail_silently=True,
        )

        instance.thank_you_sent = True
        instance.save(update_fields=["thank_you_sent"])


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    # IMPORTANT: skip during loaddata
    if kwargs.get("raw", False):
        return

    if created:
        Profile.objects.get_or_create(user=instance)
