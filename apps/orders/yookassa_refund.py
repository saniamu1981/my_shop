import uuid
import logging
from decimal import Decimal

from yookassa import Configuration, Refund
from yookassa.domain.exceptions import ApiError

from django.conf import settings

logger = logging.getLogger(__name__)

Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


def create_refund(payment_id, amount):
    """
    Создаёт возврат в ЮKassa.
    payment_id — ID платежа в ЮKassa (order.payment_id)
    amount — Decimal или строка, например Decimal('1699.00')
    Возвращает dict с данными возврата или None при ошибке.
    """
    if not payment_id:
        logger.error('ЮKassa: не указан payment_id')
        return None

    try:
        refund = Refund.create({
            "payment_id": payment_id,
            "amount": {
                "value": f"{Decimal(amount):.2f}",
                "currency": "RUB",
            },
        }, uuid.uuid4())

        logger.info(
            f'ЮKassa: возврат создан для платежа {payment_id}, '
            f'refund_id={refund.id}, статус={refund.status}'
        )

        return {
            'id': refund.id,
            'status': refund.status,
            'amount': refund.amount.value,
        }

    except ApiError as e:
        logger.error(f'ЮKassa: ошибка возврата {payment_id}: {e}')
        return None
    except Exception as e:
        logger.error(f'ЮKassa: исключение при возврате {payment_id}: {e}', exc_info=True)
        return None