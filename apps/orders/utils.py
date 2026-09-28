import json
import requests
from django.conf import settings


def clean_phone_dadata(phone: str) -> dict:
    """
    Проверяет и стандартизирует телефон через Dadata Clean API.
    Возвращает словарь с результатом.
    """
    if not phone:
        return {'valid': False, 'reason': 'empty'}

    # Убираем лишние символы, оставляем цифры
    digits = ''.join(filter(str.isdigit, phone))

    # Простая проверка формата РФ (11 цифр, начинается с 7 или 8)
    if len(digits) == 11 and digits[0] == '8':
        digits = '7' + digits[1:]  # 8XXX -> 7XXX
    if not (len(digits) == 11 and digits[0] == '7'):
        return {'valid': False, 'reason': 'format'}

    url = "https://cleaner.dadata.ru/api/v1/clean/phone"
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Authorization': f'Token {settings.DADATA_API_KEY}',
        'X-Secret': settings.DADATA_SECRET_KEY,
    }

    try:
        response = requests.post(
            url,
            headers=headers,
            data=json.dumps([digits]),  # Тело запроса — список строк [citation:3]
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()

        if not data or not isinstance(data, list):
            return {'valid': False, 'reason': 'empty_response'}

        result = data[0]
        qc = result.get('qc', 1)  # Код качества [citation:3]

        # qc = 0 — уверенно распознан российский номер
        if qc == 0:
            return {
                'valid': True,
                'phone': result.get('phone', ''),
                'provider': result.get('provider', ''),
                'region': result.get('region', ''),
                'qc': qc,
            }
        else:
            return {
                'valid': False,
                'reason': 'dadata_qc',
                'qc': qc,
                'raw': result,
            }

    except requests.RequestException as e:
        # Если Dadata недоступна — не блокируем заказ, пропускаем
        print(f'[Dadata] Ошибка запроса: {e}')
        return {'valid': True, 'phone': phone, 'skipped': True}