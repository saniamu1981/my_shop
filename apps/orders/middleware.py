from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


class AutoCancelUnpaidOrdersMiddleware:
    """
    Проверяет и отменяет просроченные неоплаченные заказы
    при любом заходе на сайт.
    """

    # Интервал проверки (в секундах) — чтобы не грузить БД на каждый запрос
    CHECK_INTERVAL = 60  # раз в минуту

    # Через сколько часов отменять неоплаченный заказ
    CANCEL_AFTER_HOURS = 72  # ← поменяйте на 72 на проде

    def __init__(self, get_response):
        self.get_response = get_response
        self._last_check = None

    def __call__(self, request):
        # Проверяем не чаще раза в CHECK_INTERVAL секунд
        now = timezone.now()
        if self._last_check is None or (now - self._last_check).total_seconds() > self.CHECK_INTERVAL:
            self._last_check = now
            self._cancel_expired_orders()

        return self.get_response(request)

    def _cancel_expired_orders(self):
        """Отменяет все просроченные неоплаченные заказы."""
        from apps.orders.models import Order

        cutoff = timezone.now() - timedelta(hours=self.CANCEL_AFTER_HOURS)

        orders = Order.objects.filter(
            paid=False,
            status__in=['created', 'paid', 'confirmed'],
            created__lt=cutoff,
        )
        print(f"[AutoCancel] Найдено: {orders.count()}")

        for order in orders:
            print(f"[AutoCancel] Отменяю #{order.id}")
            result = order.cancel()
            print(f"[AutoCancel] Результат: {result}")
            try:
                if order.cancel():
                    logger.info(
                        f'Заказ #{order.id}: автоматически отменён '
                        f'(не оплачен, старше {self.CANCEL_AFTER_HOURS} ч.)'
                    )
            except Exception as e:
                logger.error(f'Ошибка автоотмены заказа #{order.id}: {e}')