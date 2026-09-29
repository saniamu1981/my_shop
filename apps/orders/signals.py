from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone
import logging

from .models import Order
from delivery.services import CDEKService

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Order)
def track_old_status(sender, instance, **kwargs):
    """Запоминает старый статус до сохранения."""
    if instance.pk:
        try:
            old = Order.objects.get(pk=instance.pk)
            instance._old_status = old.status
        except Order.DoesNotExist:
            instance._old_status = None


@receiver(post_save, sender=Order)
def auto_create_cdek_order(sender, instance, created, **kwargs):
    """Автоматически создаёт заказ в СДЭК при смене статуса на 'confirmed'."""
    if created:
        return

    old_status = getattr(instance, '_old_status', None)

    # Реагируем только на переход в 'confirmed'
    if old_status == 'confirmed' or instance.status != 'confirmed':
        return

    # Уже создан в СДЭК — пропускаем
    if instance.cdek_order_uuid:
        return

    # Только для доставки СДЭК
    if instance.delivery_method != 'sdek':
        return

    # Нужен код ПВЗ
    if not instance.delivery_point_code:
        logger.warning(f'Заказ #{instance.id}: не указан код ПВЗ СДЭК')
        return

    # Создаём заказ в СДЭК
    try:
        service = CDEKService()
        result = service.create_order(instance)
        if result:
            logger.info(f'Заказ #{instance.id}: создан в СДЭК ({instance.cdek_number})')

            # Push-уведомление клиенту
            if instance.user:
                try:
                    from apps.accounts.utils import send_push_safe
                    payload = {
                        "head": "📦 Заказ зарегистрирован в СДЭК",
                        "body": f"Заказ №{instance.id}: ожидается передача в СДЭК",
                        "icon": "/static/icons/icon-192x192.png",
                        "url": f"/orders/{instance.id}/",
                    }
                    send_push_safe(instance.user, payload)
                except Exception as e:
                    logger.error(f'Ошибка push для заказа #{instance.id}: {e}', exc_info=True)
    except Exception as e:
        logger.error(f'Заказ #{instance.id}: ошибка создания в СДЭК: {e}', exc_info=True)