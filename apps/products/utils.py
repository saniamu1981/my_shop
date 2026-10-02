import requests
from django.conf import settings
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
    """Определяет город по IP через DaData."""
    if not ip or ip in ('127.0.0.1', '::1'):
        return {'city': '', 'region': '', 'country': ''}

    try:
        response = requests.get(
            'https://suggestions.dadata.ru/suggestions/api/4_1/rs/iplocate/address',
            headers={
                'Authorization': f'Token {settings.DADATA_API_KEY}',
                'X-Secret': settings.DADATA_SECRET_KEY,
            },
            params={'ip': ip},
            timeout=3,
        )
        if response.status_code == 200:
            data = response.json()
            if data.get('location'):
                loc = data['location']['data']
                return {
                    'city': loc.get('city', '') or loc.get('settlement', ''),
                    'region': loc.get('region_with_type', ''),
                    'country': loc.get('country', ''),
                }
    except Exception as e:
        logger.error(f'DaData IP lookup error for {ip}: {e}')

    return {'city': '', 'region': '', 'country': ''}