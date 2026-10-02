from django.utils.deprecation import MiddlewareMixin
from .models import SiteView
from .utils import get_client_ip, get_city_by_ip
import logging

logger = logging.getLogger(__name__)


class SiteViewMiddleware(MiddlewareMixin):
    """Сохраняет каждый просмотр страницы сайта."""

    # Страницы, которые НЕ считаем
    EXCLUDED_PREFIXES = (
        '/admin/',
        '/admin-panel/',
        '/static/',
        '/media/',
        '/delivery/api/',
        '/products/sizes/',
        '/products/toggle-favorite/',
        '/webpush/',
        '/serviceworker.js',
        '/manifest.json',
        '/favicon.ico',
        '/favicon.svg',
        '/robots.txt',
        '/accounts/login/',
        '/accounts/logout/',
        '/accounts/signup/',
        '/accounts/password/',
        '/accounts/confirm-email/',
        '/accounts/check-phone/',
    )

    def process_request(self, request):
        # Пропускаем исключённые пути
        path = request.path
        if any(path.startswith(prefix) for prefix in self.EXCLUDED_PREFIXES):
            return None

        # Пропускаем админов
        if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
            return None

        # Только GET-запросы
        if request.method != 'GET':
            return None

        try:
            ip = get_client_ip(request)
            geo = get_city_by_ip(ip)

            if not request.session.session_key:
                request.session.create()

            SiteView.objects.create(
                path=path,
                user=request.user if request.user.is_authenticated else None,
                session_key=request.session.session_key or '',
                ip_address=ip or None,
                city=geo['city'],
                region=geo['region'],
                country=geo['country'],
            )
        except Exception as e:
            logger.error(f'SiteViewMiddleware error: {e}')

        return None