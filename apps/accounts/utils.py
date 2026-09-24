# apps/accounts/utils.py
from webpush import send_user_notification


def send_push_safe(user, payload, ttl=1000):
    email = getattr(user, 'email', user)
    print(f'[push] >>> вызов для {email}, webpush_enabled={getattr(user, "webpush_enabled", "???")}')

    if not getattr(user, 'webpush_enabled', True):
        print(f'[push] SKIP {email}: отключено пользователем')
        return False

    try:
        send_user_notification(user=user, payload=payload, ttl=ttl)
        print(f'[push] OK — отправлено {email}')
        return True
    except Exception as e:
        print(f'[push] ERROR {email}: {type(e).__name__} — {e}')
        return False