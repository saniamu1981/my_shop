from celery import shared_task
from django.utils import timezone
from datetime import timedelta

from .models import Order
from apps.accounts.utils import send_push_safe
import logging

logger = logging.getLogger(__name__)


@shared_task
def cancel_unpaid_orders():
    """Отменяет неоплаченные заказы старше 72 часов."""
    cutoff = timezone.now() - timedelta(hours=72)

    orders = Order.objects.filter(
        paid=False,
        status__in=['created', 'paid', 'confirmed'],
        created__lt=cutoff,
    )

    cancelled = 0
    for order in orders:
        try:
            was_paid = order.paid

            if order.cancel():
                cancelled += 1
                logger.info(f'Заказ #{order.id}: автоматически отменён (не оплачен, старше 72 часов)')

                # Push-уведомление клиенту
                try:
                    if order.user:
                        body = f"Заказ №{order.id} отменён без оплаты."
                        payload = {
                            "head": "❌ Заказ отменён",
                            "body": body,
                            "icon": "/static/icons/icon-192x192.png",
                            "url": f"/orders/{order.id}/",
                        }
                        send_push_safe(order.user, payload)
                except Exception as e:
                    logger.error(f'Push error (auto-cancel): {e}')
        except Exception as e:
            logger.error(f'Ошибка отмены заказа #{order.id}: {e}')

    return f'Отменено заказов: {cancelled}'