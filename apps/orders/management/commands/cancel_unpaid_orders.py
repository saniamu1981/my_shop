from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from apps.orders.models import Order
from apps.accounts.utils import send_push_safe
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Отменяет неоплаченные заказы старше 72 часов'

    def handle(self, *args, **options):
        cutoff = timezone.now() - timedelta(hours=72)

        # Заказы, которые:
        # - не оплачены
        # - в статусе created/paid/confirmed
        # - созданы больше 72 часов назад
        orders = Order.objects.filter(
            paid=False,
            status__in=['created', 'paid', 'confirmed'],
            created__lt=cutoff,
        )

        cancelled = 0
        for order in orders:
            try:
                # Отменяем заказ
                if order.cancel():
                    cancelled += 1
                    logger.info(
                        f'Заказ #{order.id}: автоматически отменён '
                        f'(не оплачен, старше 72 часов)'
                    )

                    # Push-уведомление клиенту
                    try:
                        if order.user:
                            payload = {
                                "head": "❌ Заказ отменён",
                                "body": f"Заказ №{order.id} отменён без оплаты.",
                                "icon": "/static/icons/icon-192x192.png",
                                "url": f"/orders/{order.id}/",
                            }
                            send_push_safe(order.user, payload)
                    except Exception as e:
                        logger.error(f'Push error (auto-cancel): {e}')
            except Exception as e:
                logger.error(f'Ошибка отмены заказа #{order.id}: {e}')

        self.stdout.write(
            self.style.SUCCESS(
                f'Отменено неоплаченных заказов: {cancelled}'
            )
        )