import requests
import json
import logging
from django.core.cache import cache
from django.conf import settings
from django.utils import timezone
from .models import DeliveryPoint

logger = logging.getLogger(__name__)


class CDEKService:
    """Сервис для работы с API СДЭК"""

    BASE_URL = 'https://api.cdek.ru/v2'
    TEST_BASE_URL = 'https://api.edu.cdek.ru/v2'

    def __init__(self):
        self.client_id = settings.CDEK_CLIENT_ID
        self.client_secret = settings.CDEK_CLIENT_SECRET
        self.test_mode = getattr(settings, 'CDEK_TEST_MODE', True)
        self.base_url = self.TEST_BASE_URL if self.test_mode else self.BASE_URL
        self._token = None

    # ============================================================
    # АВТОРИЗАЦИЯ
    # ============================================================

    def _get_token(self):
        """Получение токена авторизации"""
        if self._token:
            return self._token

        cache_key = 'cdek_token'
        token = cache.get(cache_key)
        if token:
            self._token = token
            return token

        url = f'{self.base_url}/oauth/token'
        data = {
            'grant_type': 'client_credentials',
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }

        try:
            response = requests.post(url, data=data, timeout=30)
            response.raise_for_status()
            result = response.json()
            token = result.get('access_token')

            if token:
                cache.set(cache_key, token, 3600)  # Сохраняем на 1 час
                self._token = token
                return token
        except Exception as e:
            logger.error(f'Ошибка получения токена СДЭК: {e}')
            return None

    def _headers(self):
        token = self._get_token()
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }

    def register_webhook(self, url, event_type='ORDER_STATUS'):
        """Регистрирует вебхук в СДЭК."""
        payload = {
            'url': url,
            'type': event_type,
        }
        response = requests.post(
            f'{self.base_url}/webhooks',
            headers=self._headers(),
            json=payload,
            timeout=30,
        )
        return response.json()

    # ============================================================
    # ПУНКТЫ ВЫДАЧИ
    # ============================================================

    def get_delivery_points(self, city_code=None, city_name=None):
        """Получение списка пунктов выдачи"""
        token = self._get_token()
        if not token:
            return []

        url = f'{self.base_url}/deliverypoints'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        params = {
            'type': 'PVZ',
            'is_dressing_room': True,
            'page': 0,
            'size': 100
        }

        if city_code:
            params['city_code'] = city_code
        elif city_name:
            params['city'] = city_name

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            points = []
            for item in data.get('items', []):
                point = {
                    'code': item.get('code'),
                    'name': item.get('name'),
                    'address': self._format_address(item),
                    'city': item.get('location', {}).get('city'),
                    'city_code': item.get('location', {}).get('city_code'),
                    'latitude': item.get('location', {}).get('latitude'),
                    'longitude': item.get('location', {}).get('longitude'),
                    'phone': item.get('phone', ''),
                    'work_time': self._format_work_time(item.get('work_time', []))
                }
                points.append(point)

                DeliveryPoint.objects.update_or_create(
                    code=point['code'],
                    defaults={
                        'name': point['name'],
                        'address': point['address'],
                        'city': point['city'],
                        'city_code': point['city_code'],
                        'latitude': point['latitude'],
                        'longitude': point['longitude'],
                        'phone': point['phone'],
                        'work_time': point['work_time'],
                        'is_active': True
                    }
                )

            return points
        except Exception as e:
            logger.error(f'Ошибка получения пунктов выдачи СДЭК: {e}')
            return []

    def _format_address(self, item):
        """Форматирование адреса"""
        location = item.get('location', {})
        address_parts = []

        if location.get('city'):
            address_parts.append(f'г. {location["city"]}')
        if location.get('street'):
            address_parts.append(f'ул. {location["street"]}')
        if location.get('house'):
            address_parts.append(f'д. {location["house"]}')
        if location.get('block'):
            address_parts.append(f'корп. {location["block"]}')
        if location.get('flat'):
            address_parts.append(f'кв. {location["flat"]}')

        return ', '.join(address_parts) if address_parts else item.get('address', '')

    def _format_work_time(self, work_time):
        """Форматирование времени работы"""
        if not work_time:
            return ''

        times = []
        for item in work_time[:1]:  # Берем только обычное время (не интервалы)
            if item.get('time'):
                times.append(item['time'])

        return ' '.join(times) if times else ''

    # ============================================================
    # РАСЧЁТ СТОИМОСТИ
    # ============================================================

    def calculate_delivery_price(self, city_code=None, city_name=None):
        """Расчет стоимости доставки"""
        token = self._get_token()
        if not token:
            return None

        url = f'{self.base_url}/calculator/tarifflist'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        data = {
            'type': 1,  # Доставка
            'currency': 1,  # Рубли
            'from_location': {
                'code': settings.SHOP_CITY_CODE
            },
            'to_location': {}
        }

        if city_code:
            data['to_location']['code'] = city_code
        elif city_name:
            data['to_location']['city'] = city_name

        try:
            response = requests.post(url, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            result = response.json()

            tariffs = result.get('tariff_codes', [])
            if tariffs:
                return tariffs[0].get('delivery_sum', 0)
            return None
        except Exception as e:
            logger.error(f'Ошибка расчета стоимости доставки СДЭК: {e}')
            return None

    # ============================================================
    # ГОРОДА
    # ============================================================

    def get_city_code(self, city_name):
        """Получение кода города по названию"""
        token = self._get_token()
        if not token:
            return None

        url = f'{self.base_url}/location/cities'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        params = {
            'city': city_name,
            'country_codes': 'RU'
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data:
                return data[0].get('code')
            return None
        except Exception as e:
            logger.error(f'Ошибка получения кода города СДЭК: {e}')
            return None

    # ============================================================
    # СОЗДАНИЕ ЗАКАЗА В СДЭК
    # ============================================================

    def create_order(self, order, tariff_code=136):
        # Защита от повторного создания
        if order.cdek_order_uuid:
            logger.info(f'Заказ #{order.id} уже создан в СДЭК ({order.cdek_number})')
            return {'entity': {'uuid': order.cdek_order_uuid, 'cdek_number': order.cdek_number}}
        """
        Создаёт заказ в СДЭК на основе объекта Order.

        tariff_code:
            136 — Посылка склад-склад (ПВЗ → ПВЗ)
            137 — Посылка склад-дверь (ПВЗ → адрес)
            138 — Посылка дверь-склад (адрес → ПВЗ)
            139 — Посылка дверь-дверь (адрес → адрес)

        Возвращает dict с ответом или None при ошибке.
        """
        if not order.delivery_point_code:
            logger.error(f'Заказ #{order.id}: не указан код ПВЗ СДЭК')
            return None

        # Тип доставки: если самовывоз — склад-склад (136), иначе склад-дверь (137)
        if tariff_code is None:
            tariff_code = 136 if order.delivery_method == 'pickup' else 137

        packages = self._build_packages(order)
        if not packages:
            logger.error(f'Заказ #{order.id}: нет товаров для отправки')
            return None

        payload = {
            'type': 1,                      # Интернет-магазин
            'number': str(order.id),        # Ваш номер заказа
            'tariff_code': tariff_code,
            'comment': f'Заказ №{order.id}',
            'delivery_point': order.delivery_point_code,  # Код ПВЗ
            'recipient': {
                'name': f'{order.first_name} {order.last_name}'.strip() or order.email,
                'phones': [{'number': order.phone}],
                'email': order.email,
            },
            'packages': packages,
            'from_location': {'code': int(settings.SHOP_CITY_CODE)},
        }

        try:
            response = requests.post(
                f'{self.base_url}/orders',
                headers=self._headers(),
                json=payload,
                timeout=30,
            )
            data = response.json()
            logger.info(f'СДЭК создание заказа #{order.id}: {response.status_code} — {data}')

            if response.status_code in (200, 202):
                entity = data.get('entity', {})
                order.cdek_order_uuid = entity.get('uuid')
                order.cdek_number = entity.get('cdek_number')
                order.save(update_fields=['cdek_order_uuid', 'cdek_number'])
                return data

            logger.error(f'СДЭК ошибка создания заказа #{order.id}: {data}')
            return None

        except Exception as e:
            logger.error(f'СДЭК исключение при создании заказа #{order.id}: {e}', exc_info=True)
            return None

    def _build_packages(self, order):
        """Формирует список упаковок с товарами для API СДЭК."""
        items = []
        total_weight = 0

        for item in order.items.all():
            # Вес по умолчанию 500 г, если у товара нет поля weight
            weight = getattr(item.product, 'weight', None) or 500
            total_weight += weight * item.quantity

            items.append({
                'name': item.product.name[:255],
                'ware_key': item.product.sku or str(item.product.id),
                'payment': {'value': 0},   # Уже оплачено
                'cost': float(item.price),
                'weight': weight,
                'amount': item.quantity,
            })

        if not items:
            return []

        return [{
            'number': f'{order.id}-1',
            'weight': total_weight or 1000,
            'items': items,
        }]

    # ============================================================
    # СТАТУСЫ ЗАКАЗА
    # ============================================================

    def get_order_status(self, order_uuid):
        """Получает текущий статус заказа из СДЭК по UUID."""
        try:
            response = requests.get(
                f'{self.base_url}/orders/{order_uuid}',
                headers=self._headers(),
                timeout=30,
            )
            if response.status_code != 200:
                logger.warning(f'СДЭК get_order_status: {response.status_code}')
                return None

            data = response.json()
            entity = data.get('entity', {})
            statuses = entity.get('statuses', [])
            last_status = statuses[-1] if statuses else {}

            return {
                'status_code': last_status.get('code'),
                'status_name': last_status.get('name'),
                'cdek_number': entity.get('cdek_number'),
            }
        except Exception as e:
            logger.error(f'СДЭК ошибка получения статуса: {e}', exc_info=True)
            return None

    def sync_order_status(self, order):
        """
        Синхронизирует статус заказа из СДЭК в модель Order.
        Возвращает True, если что-то обновилось.
        """
        if not order.cdek_order_uuid:
            return False

        status_data = self.get_order_status(order.cdek_order_uuid)
        if not status_data:
            return False

        old_status = order.status
        old_cdek_status = order.cdek_status_name

        order.cdek_status_code = status_data.get('status_code') or order.cdek_status_code
        order.cdek_status_name = status_data.get('status_name') or order.cdek_status_name
        order.cdek_number = status_data.get('cdek_number') or order.cdek_number

        new_status = self._map_cdek_status(status_data.get('status_code'))
        if new_status and new_status != order.status:
            order.status = new_status
            if new_status == 'delivered' and not order.delivered_at:
                order.delivered_at = timezone.now()

        order.save(update_fields=[
            'cdek_status_code', 'cdek_status_name', 'cdek_number',
            'status', 'delivered_at',
        ])

        # Логируем изменения
        if order.status != old_status:
            logger.info(
                f'Заказ #{order.id}: статус изменён с "{old_status}" на "{order.status}" '
                f'(СДЭК: {old_cdek_status} → {order.cdek_status_name})'
            )

        # Уведомляем клиента при смене статуса
        if order.status != old_status and order.user:
            try:
                from apps.accounts.utils import send_push_safe
                payload = {
                    "head": "📦 Статус заказа обновлён",
                    "body": f"Заказ №{order.id}: {order.cdek_status_name}",
                    "icon": "/static/icons/icon-192x192.png",
                    "url": f"/orders/{order.id}/",
                }
                send_push_safe(order.user, payload)
            except Exception as e:
                logger.error(f'Ошибка push-уведомления для заказа #{order.id}: {e}')

        return True

    def delete_order(self, order):
        """
        Удаляет заказ в СДЭК. Возможно только если заказ ещё не принят физически
        (статус CREATED или ACCEPTED).
        """
        if not order.cdek_order_uuid:
            return True  # Нечего удалять

        try:
            response = requests.delete(
                f'{self.base_url}/orders/{order.cdek_order_uuid}',
                headers=self._headers(),
                timeout=30,
            )

            if response.status_code in (200, 202, 204):
                logger.info(f'Заказ #{order.id} удалён в СДЭК')
                order.cdek_order_uuid = None
                order.cdek_number = None
                order.cdek_status_code = None
                order.cdek_status_name = None
                order.save(update_fields=[
                    'cdek_order_uuid', 'cdek_number', 'cdek_status_code', 'cdek_status_name',
                ])
                return True

            logger.error(f'СДЭК не удалось удалить заказ #{order.id}: {response.status_code} — {response.text}')
            return False

        except Exception as e:
            logger.error(f'СДЭК исключение при удалении заказа #{order.id}: {e}', exc_info=True)
            return False

    def _map_cdek_status(self, cdek_code):
        """
        Маппинг кодов статусов СДЭК на статусы Order.

        Логика:
        - CREATED / ACCEPTED — заказ создан в СДЭК, но ещё не принят → 'confirmed'
        - RECEIVED_AT_SHIPMENT_WAREHOUSE / SENT_TO_TRANSIT — реально в пути → 'shipped'
        - DELIVERED — доставлен → 'delivered'
        - RETURNED — возврат → 'cancelled'
        """
        if not cdek_code:
            return None

        mapping = {
            # Заказ создан в СДЭК, но ещё не принят в доставку
            'CREATED': 'confirmed',
            'ACCEPTED': 'confirmed',  # ← исправлено

            # Заказ реально в пути
            'RECEIVED_AT_SHIPMENT_WAREHOUSE': 'shipped',
            'SENT_TO_TRANSIT': 'shipped',
            'RECEIVED_AT_TRANSIT_WAREHOUSE': 'shipped',
            'ACCEPTED_AT_TRANSIT_WAREHOUSE': 'shipped',
            'DELIVERED_TO_TRANSIT_WAREHOUSE': 'shipped',
            'SENT_TO_DESTINATION': 'shipped',

            # Доставлен
            'DELIVERED': 'delivered',

            # Проблемы
            'NOT_DELIVERED': 'shipped',
            'RETURNED': 'cancelled',
            'RETURNED_TO_SENDER': 'cancelled',
        }
        return mapping.get(cdek_code)