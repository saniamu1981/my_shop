import requests
from django.conf import settings
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


def get_client_ip(request):
    """Возвращает IP клиента с учётом прокси."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip


def get_city_by_ip(ip):
    """
    Определяет город по IP через ip-api.com.
    Кэширует результат на 24 часа.
    """
    if not ip or ip in ('127.0.0.1', '::1'):
        return {'city': '', 'region': '', 'country': ''}

    # Кэш на сутки
    cache_key = f'geoip_{ip}'
    cached = cache.get(cache_key)
    if cached:
        return cached

    try:
        response = requests.get(
            f'http://ip-api.com/json/{ip}',
            params={
                'fields': 'status,country,regionName,city',
                'lang': 'ru',
            },
            timeout=3,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                result = {
                    'city': data.get('city', '') or '',
                    'region': data.get('regionName', '') or '',
                    'country': data.get('country', '') or '',
                }
                cache.set(cache_key, result, 60 * 60 * 24)  # 24 часа
                return result
    except Exception as e:
        logger.error(f'ip-api error for {ip}: {e}')

    # Если что-то пошло не так — возвращаем пустой результат
    # (не кэшируем, чтобы попробовать снова в следующий раз)
    return {'city': '', 'region': '', 'country': ''}