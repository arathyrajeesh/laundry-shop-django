from django.core.management.base import BaseCommand
from shop.utils import notify_delayed_orders

class Command(BaseCommand):
    help = "Check delayed orders and notify customers"

    def handle(self, *args, **kwargs):
        notify_delayed_orders()
        self.stdout.write(self.style.SUCCESS("Delayed orders checked successfully"))
