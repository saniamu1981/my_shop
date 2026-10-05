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
        from apps.orders.models import Order
        from django.utils import timezone
        from datetime import timedelta
        from django.db import connection

        cutoff = timezone.now() - timedelta(hours=72)

        orders = Order.objects.filter(
            paid=False,
            status__in=['created', 'paid', 'confirmed'],
            created__lt=cutoff,
        )