import requests

# Данные из настроек
client_id = 'f09d1d32d25e45a0b9dccf8ec851ecfa'
client_secret = '5ee190b18e3e416e97abffbb9a2f7a42'
code = 'ft37von2iknup4sz'  # Код из ссылки выше

response = requests.post(
    'https://oauth.yandex.ru/token',
    data={
        'grant_type': 'authorization_code',
        'code': code,
        'client_id': client_id,
        'client_secret': client_secret
    }
)

token_data = response.json()
access_token = token_data.get('access_token')
print(f"Access Token: {access_token}")