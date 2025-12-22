from django import template

register = template.Library()

@register.filter
def get_value(dictionary, key):
    """Get a value from a dictionary by key."""
    if isinstance(dictionary, dict):
        return dictionary.get(key)
    return None