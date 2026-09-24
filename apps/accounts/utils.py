# apps/accounts/utils.py
from webpush import send_user_notification


def send_push_safe(user, payload, ttl=1000):
    """Отправляет push только если пользователь их не отключил.
    Возвращает True при успешной отправке, False — если пропустили/ошибка."""
    if not getattr(user, 'webpush_enabled', True):
        return False
    try:
        send_user_notification(user=user, payload=payload, ttl=ttl)
        return True
    except Exception as e:
        print(f'Webpush error for {getattr(user, "email", user)}: {e}')
        return False