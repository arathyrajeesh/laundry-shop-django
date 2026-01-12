from django.utils import timezone
from models import Order,Notification

def create_shop_pending_notifications(shop):
    pending_orders = Order.objects.filter(
        shop=shop,
        payment_status="Completed",
        cloth_status="Pending",
        pending_notification_sent=False
    ).select_related("user")

    for order in pending_orders:
        Notification.objects.create(
            shop=shop,
            title=f"Pending Order #{order.id}",
            message=f"New order from {order.user.username}. Please start processing.",
            icon="fas fa-hourglass-start",
            color="#f59e0b"
        )

        order.pending_notification_sent = True
        order.save(update_fields=["pending_notification_sent"])
