# apps/accounts/adapters.py
import logging
from allauth.account.adapter import DefaultAccountAdapter

logger = logging.getLogger(__name__)


class CustomAccountAdapter(DefaultAccountAdapter):
    """Не даём падать сайту, если письмо не отправилось."""

    def send_mail(self, template_prefix, email, context):
        try:
            return super().send_mail(template_prefix, email, context)
        except Exception as e:
            logger.error(
                f'[allauth] Ошибка отправки письма на {email}: '
                f'{type(e).__name__} — {e}'
            )
            # Ничего не выбрасываем — сайт продолжит работать