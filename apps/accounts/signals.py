from django.db.models.signals import post_save
from django.contrib.auth import get_user_model
from django.dispatch import receiver
from apps.orders.models import Cart

User = get_user_model()

@receiver(post_save, sender=User)
def create_user_cart(sender, instance, created, **kwargs):
    """Создает корзину для нового пользователя"""
    if created:
        Cart.objects.create(user=instance)