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
    return range(int(value))


@register.filter(name="subtract")
def subtract(value, arg):
    return value - arg


@register.filter(name="divide_02")
def divide_02(value, arg):
    if arg == 0:
        return f"{(float(value) / 1.0 * 100):.2f}"
    return f"{(float(value) * 100.0 / float(arg)):.2f}"


@register.filter(name="div_100")
def div_100(value, arg):
    if not arg:
        return float(value) * 100.0
    return float(value) * 100.0 / float(arg)


@register.filter(name="div")
def div(value, arg):
    if not arg:
        return float(value) * 1.0
    return float(value) * 1.0 / float(arg)


@register.filter(name="div_int")
def div_int(value, arg):
    if not arg:
        return int(value)
    return int(value) / int(arg)


@register.filter(name="mod")
def mod(value, arg):
    if not arg:
        return int(value)
    return int(value) % int(arg)


@register.filter
def replace_comma_to_dot(value):
    if value is None:
        return "0"
    return str(value).replace(",", ".")
