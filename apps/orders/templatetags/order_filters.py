# apps/orders/templatetags/order_filters.py
from django import template
from apps.products.models import Review

register = template.Library()

@register.filter
def has_user_review(item, user):
    """Проверяет, оставил ли пользователь отзыв на этот товар"""
    return Review.objects.filter(product=item.product, user=user).exists()