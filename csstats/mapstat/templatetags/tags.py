from django import template

register = template.Library()


@register.simple_tag
def elo_class(elo):
    if elo < 5000:
        return "elo-gray"
    elif elo < 10000:
        return "elo-blue"
    elif elo < 15000:
        return "elo-dark-blue"
    elif elo < 20000:
        return "elo-purple"
    elif elo < 25000:
        return "elo-pink"
    elif elo < 25000:
        return "elo-red"
    return "elo-yellow"
