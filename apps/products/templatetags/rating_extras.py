from django import template

register = template.Library()


@register.filter
def star_states(rating):
    try:
        value = float(rating)
    except (TypeError, ValueError):
        value = 0.0

    states = []
    for i in range(1, 6):
        if value >= i:
            states.append('full')
            continue
        remainder = value - (i - 1)
        if remainder <= 0.2:
            states.append('empty')
        elif remainder <= 0.7:
            states.append('half')
        else:
            states.append('full')
    return states