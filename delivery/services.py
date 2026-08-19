import requests
import json
from django.core.cache import cache
from django.conf import settings
from .models import DeliveryPoint


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
            print(f'Ошибка получения токена СДЭК: {e}')
            return None

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

                # Сохраняем в кэш (опционально)
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
            print(f'Ошибка получения пунктов выдачи СДЭК: {e}')
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
            print(f'Ошибка расчета стоимости доставки СДЭК: {e}')
            return None

    def get_city_code(self, city_name):
        """Получение кода города по названию"""
        token = self._get_token()
        if not token:
            return None

        url = f'{self.base_url}/city'
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        params = {
            'city': city_name,
            'country_code': 'RU'
        }

        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if data:
                return data[0].get('code')
            return None
        except Exception as e:
            print(f'Ошибка получения кода города СДЭК: {e}')
            return None