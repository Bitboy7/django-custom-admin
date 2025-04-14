from django import template

register = template.Library()

@register.filter
def get_range(value):
    """
    Generate a range from 0 to the given value
    """
    return range(value)

@register.filter
def get_item(list_or_dict, key):
    """
    Get an item from a list or dictionary by key/index
    """
    try:
        return list_or_dict[int(key)]
    except (IndexError, ValueError, TypeError):
        return None