import requests
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

YOOKASSA_API = 'https://api.yookassa.ru/v3'


def cancel_payment(payment_id):
    import uuid
    """
    Отменяет холдирование платежа (только для статуса waiting_for_capture).
    Возвращает True при успехе.
    """
    response = requests.post(
        f'{YOOKASSA_API}/payments/{payment_id}/cancel',
        auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
        headers={
            'Idempotence-Key': str(uuid.uuid4()),
            'Content-Type': 'application/json',
        },
        timeout=30,
    )
    if response.status_code == 200:
        logger.info(f'ЮKassa: платёж {payment_id} отменён (холдирование снято)')
        return True
    logger.error(f'ЮKassa: ошибка отмены платежа {payment_id}: {response.status_code} — {response.text}')
    return False


def create_refund(payment_id, amount, currency='RUB'):
    """
    Создаёт возврат для успешного платежа (статус succeeded).
    amount — Decimal или строка, например '1699.00'.
    """
    response = requests.post(
        f'{YOOKASSA_API}/refunds',
        auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
        headers={
            'Idempotence-Key': str(uuid.uuid4()),
            'Content-Type': 'application/json',
        },
        json={
            'payment_id': payment_id,
            'amount': {
                'value': str(amount),
                'currency': currency,
            },
        },
        timeout=30,
    )
    if response.status_code == 200:
        data = response.json()
        logger.info(f'ЮKassa: возврат создан для платежа {payment_id}, refund_id={data.get("id")}')
        return data
    logger.error(f'ЮKassa: ошибка возврата {payment_id}: {response.status_code} — {response.text}')
    return None

def get_payment_status(payment_id):
    """Возвращает статус платежа в ЮKassa."""
    response = requests.get(
        f'{YOOKASSA_API}/payments/{payment_id}',
        auth=(settings.YOOKASSA_SHOP_ID, settings.YOOKASSA_SECRET_KEY),
        timeout=30,
    )
    if response.status_code == 200:
        return response.json().get('status')
    return None