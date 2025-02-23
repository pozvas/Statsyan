from django import template
register = template.Library()


@register.filter
def get_value_from_dict(dict_data, key):
    return dict_data.get(key)


@register.filter
def get_or_else(value, or_else):
    return or_else if value is None else value
