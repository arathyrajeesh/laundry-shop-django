from django.utils import timezone

from laundry_shop.shop.models import ShopNotification,Order

def send_overdue_notifications():
    now = timezone.now()

    overdue_orders = Order.objects.filter(
        payment_status="Completed",
        delivery_date__lt=now,
        cloth_status__in=["Pending", "Washing", "Drying", "Ironing"],
        overdue_notification_sent=False
    ).select_related("shop", "user")

    for order in overdue_orders:
        ShopNotification.objects.create(
            shop=order.shop,
            title=f"Overdue Order #{order.id}",
            message=(
                f"Order for {order.user.username} "
                f"was due on {order.delivery_date.strftime('%d %b %Y %H:%M')}."
            ),
            icon="fas fa-exclamation-triangle",
            color="#e74c3c"
        )

        # ✅ Mark as notified
        order.overdue_notification_sent = True
        order.save(update_fields=["overdue_notification_sent"])
