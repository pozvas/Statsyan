from django import template

register = template.Library()


@register.filter
def get_value_from_dict(dict_data, key):
    return dict_data.get(key)


@register.filter
def get_or_else(value, or_else):
    return or_else if value is None else value


@register.filter
def get_time(seconds):
    int_seconds = int(seconds)
    return f"{int_seconds // 60}:{(int_seconds % 60):02d}"


@register.filter(name="range_from_zero")
def range_from_zero(value):
    return range(value)


@register.filter(name="subtract")
def subtract(value, arg):
    return value - arg


@register.filter(name="divide_02")
def divide_02(value, arg):
    if arg == 0:
        return f"{(value / 1.0 * 100):.2f}"
    return f"{(value * 100.0 / arg):.2f}"


@register.filter(name="div_100")
def div_100(value, arg):
    if not arg:
        return value * 100.0
    return value * 100.0 / arg


@register.filter(name="div")
def div(value, arg):
    if not arg:
        return value * 1.0
    return value * 1.0 / arg
