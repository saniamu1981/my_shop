import requests
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.conf import settings
from django.core.cache import cache
from .russia_data import REGIONS, CITIES_BY_REGION, DISTRICTS_BY_CITY

logger = logging.getLogger(__name__)


@csrf_exempt
def get_regions(request):
    """Получение списка областей/регионов из встроенного справочника"""
    return JsonResponse({'regions': REGIONS, 'source': 'local'})


@csrf_exempt
def get_cities_by_region(request):
    """Получение городов по области"""
    region_name = request.GET.get('region_name')
    if not region_name:
        return JsonResponse({'cities': [], 'error': 'Не указана область'})

    cities = CITIES_BY_REGION.get(region_name, [])
    cities_list = [{'code': city, 'name': city} for city in cities]

    return JsonResponse({'cities': cities_list, 'source': 'local'})


@csrf_exempt
def get_districts_by_city(request):
    """Получение районов по городу"""
    city_name = request.GET.get('city_name')
    if not city_name:
        return JsonResponse({'districts': [], 'error': 'Не указан город'})

    districts = DISTRICTS_BY_CITY.get(city_name, [])
    districts_list = [{'code': district, 'name': district} for district in districts]

    return JsonResponse({'districts': districts_list, 'source': 'local'})


@csrf_exempt
def get_cdek_points_by_location(request):
    """Получение пунктов выдачи СДЭК по городу и району"""
    city_name = request.GET.get('city_name')
    district_name = request.GET.get('district_name')

    if not city_name:
        return JsonResponse({'points': [], 'error': 'Не указан город'})

    # Получаем код города в СДЭК
    city_code = get_cdek_city_code(city_name)
    if not city_code:
        return JsonResponse({
            'points': [],
            'error': f'Город "{city_name}" не найден в СДЭК'
        })

    token = get_cdek_token()
    if not token:
        return JsonResponse({
            'points': [],
            'error': 'Не удалось получить токен СДЭК'
        })

    try:
        params = {
            'city_code': city_code,
            'type': 'PVZ',
            'limit': 200
        }

        response = requests.get(
            'https://api.cdek.ru/v2/deliverypoints',
            headers={'Authorization': f'Bearer {token}'},
            params=params,
            timeout=30
        )

        if response.status_code != 200:
            return JsonResponse({'points': [], 'error': 'Ошибка получения пунктов'})

        try:
            data = response.json()
        except ValueError:
            return JsonResponse({'points': [], 'error': 'Ошибка парсинга ответа'})

        if isinstance(data, list):
            delivery_points = data
        elif isinstance(data, dict):
            delivery_points = data.get('delivery_points', [])
        else:
            delivery_points = []

        if not isinstance(delivery_points, list):
            delivery_points = []

        points = []
        for item in delivery_points:
            if isinstance(item, dict):
                # Если указан район, фильтруем
                if district_name:
                    item_district = item.get('district') or item.get('sub_region')
                    if item_district and district_name.lower() not in item_district.lower():
                        continue

                point = {
                    'code': str(item.get('code', '')),
                    'name': item.get('name', 'Пункт выдачи СДЭК'),
                    'address': item.get('address', ''),
                    'full_address': item.get('full_address', ''),
                    'city': item.get('city', ''),
                    'city_code': str(item.get('city_code', '')),
                    'region': item.get('region', ''),
                    'region_code': str(item.get('region_code', '')),
                    'district': item.get('district', ''),
                    'sub_region': item.get('sub_region', ''),
                    'work_time': item.get('work_time', ''),
                    'phone': item.get('phone', ''),
                    'longitude': item.get('longitude', ''),
                    'latitude': item.get('latitude', ''),
                }
                points.append(point)

        return JsonResponse({
            'points': points,
            'total': len(points),
            'is_real_data': True
        })

    except Exception as e:
        logger.error(f"Error: {str(e)}", exc_info=True)
        return JsonResponse({'points': [], 'error': str(e)})


def get_cdek_token():
    """Получение токена доступа к API СДЭК"""
    client_id = getattr(settings, 'CDEK_CLIENT_ID', '')
    client_secret = getattr(settings, 'CDEK_CLIENT_SECRET', '')

    if not client_id or not client_secret:
        return None

    cache_key = 'cdek_access_token'
    token_data = cache.get(cache_key)
    if token_data:
        return token_data

    auth_url = 'https://api.cdek.ru/v2/oauth/token'

    try:
        response = requests.post(
            auth_url,
            data={
                'grant_type': 'client_credentials',
                'client_id': client_id,
                'client_secret': client_secret
            },
            headers={'Content-Type': 'application/x-www-form-urlencoded'},
            timeout=30
        )

        if response.status_code == 200:
            auth_data = response.json()
            token = auth_data.get('access_token')
            if token:
                expires_in = auth_data.get('expires_in', 3600)
                cache.set(cache_key, token, expires_in - 600)
                return token

        return None

    except Exception as e:
        logger.error(f"Error getting token: {str(e)}")
        return None


def get_cdek_city_code(city_name):
    """Получение кода города в СДЭК"""
    token = get_cdek_token()
    if not token:
        return None

    try:
        response = requests.get(
            'https://api.cdek.ru/v2/location/cities',
            headers={'Authorization': f'Bearer {token}'},
            params={
                'city': city_name,
                'country_codes': 'RU',
                'limit': 5
            },
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            if data and isinstance(data, list) and len(data) > 0:
                return data[0].get('code')
        return None

    except Exception as e:
        logger.error(f"Error getting city code: {str(e)}")
        return None


@csrf_exempt
def test_cdek_connection(request):
    """Тестовый эндпоинт для проверки подключения к СДЭК"""
    token = get_cdek_token()

    return JsonResponse({
        'token_obtained': bool(token),
        'cdek_connected': bool(token),
        'message': '✅ Подключение к СДЭК работает' if token else '❌ Ошибка подключения к СДЭК'
    })


@csrf_exempt
def search_cities(request):
    """Поиск городов по названию"""
    query = request.GET.get('q', '')
    if len(query) < 2:
        return JsonResponse({'cities': []})

    results = []
    for region, cities in CITIES_BY_REGION.items():
        for city in cities:
            if query.lower() in city.lower():
                results.append({
                    'code': city,
                    'name': city,
                    'region': region
                })
                if len(results) >= 20:
                    break
        if len(results) >= 20:
            break

    return JsonResponse({'cities': results})