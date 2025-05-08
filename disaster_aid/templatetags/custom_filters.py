from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """
    Get an item from a dictionary using the key.
    Usage: {{ mydict|get_item:key }}
    """
    return dictionary.get(key, 0)

@register.filter
def trim(value):
    """
    Trims whitespace from a string.
    Usage: {{ mystring|trim }}
    """
    if value:
        return value.strip()
    return value

@register.filter
def split(value, delimiter):
    """
    Splits a string by delimiter and returns a list.
    Usage: {{ mystring|split:"delimiter" }}
    """
    if value:
        return value.split(delimiter)
    return []

@register.filter
def replace(value, arg):
    """
    Replaces all occurrences of the argument in the value.
    Usage: {{ mystring|replace:"text_to_remove" }}
    """
    if value:
        return value.replace(arg, '')
    return value
