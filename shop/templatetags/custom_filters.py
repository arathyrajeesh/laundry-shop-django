from django import template
from ..models import ServiceClothPrice

register = template.Library()

@register.filter
def get_value(dictionary, key):
    """Get a value from a dictionary by key."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None

@register.filter
def get_cloth_price(service, cloth_id):
    """Get the price for a specific cloth in a service."""
    try:
        cloth_price = ServiceClothPrice.objects.filter(service=service, cloth_id=cloth_id).first()
        return cloth_price.price if cloth_price else None
    except:
        return None
    
@register.filter
def get_item(dictionary, key):
    try:
        return dictionary.get(int(key))
    except Exception:
        return None
