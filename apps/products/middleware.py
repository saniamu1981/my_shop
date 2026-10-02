from django.utils.deprecation import MiddlewareMixin
from django.utils import timezone
from datetime import timedelta
from .models import SiteView
from .utils import get_client_ip, get_city_by_ip
import logging

logger = logging.getLogger(__name__)


class SiteViewMiddleware(MiddlewareMixin):
    """Сохраняет УНИКАЛЬНЫЕ визиты (один раз на сессию)."""

    # Сколько часов считать одну сессию одним визитом
    VISIT_TIMEOUT_HOURS = 24

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
        '/wp-admin/',
        '/wp-login.php',
        '/wp-content/',
        '/xmlrpc.php',
        '/.env',
        '/.git',
        '/phpmyadmin/',
        '/admin.php',
        '/setup.php',
        '/config.php',
        '/vendor/',
        '/backup/',
        '/.well-known/',
    )

    BOT_PATTERNS = (
        'bot', 'crawler', 'spider', 'slurp',
        'googlebot', 'bingbot', 'yandexbot', 'duckduckbot',
        'baiduspider', 'sogou', 'exabot', 'ia_archiver',
        'ahrefs', 'semrush', 'mj12bot', 'dotbot', 'petalbot',
        'seznam', 'screaming frog', 'seokicks',
        'curl', 'wget', 'httpie', 'axios', 'okhttp',
        'python-requests', 'python-urllib', 'python-httpx',
        'go-http-client', 'java/', 'libwww-perl',
        'apache-httpclient', 'guzzle', 'node-fetch',
        'scanner', 'nikto', 'nmap', 'masscan', 'zgrab',
        'nuclei', 'sqlmap', 'dirbuster', 'gobuster',
        'uptimerobot', 'pingdom', 'statuscake', 'newrelic',
        'datadog', 'monitis',
        'facebookexternalhit', 'telegrambot', 'whatsapp',
        'twitterbot', 'linkedinbot', 'slackbot',
        'discordbot', 'skypeuripreview',
        'headlesschrome', 'phantomjs', 'selenium',
        'puppeteer', 'playwright',
    )

    def process_request(self, request):
        path = request.path
        if any(path.startswith(prefix) for prefix in self.EXCLUDED_PREFIXES):
            return None

        if request.method != 'GET':
            return None

        user_agent = request.META.get('HTTP_USER_AGENT', '').strip()
        if not user_agent:
            return None

        ua_lower = user_agent.lower()
        if any(pattern in ua_lower for pattern in self.BOT_PATTERNS):
            return None

        if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
            return None

        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        if not accept_language:
            return None

        # === ГЛАВНОЕ: одна сессия = один визит ===
        if not request.session.session_key:
            request.session.create()

        session_key = request.session.session_key

        # Проверяем, был ли уже визит этой сессии за последние N часов
        cutoff = timezone.now() - timedelta(hours=self.VISIT_TIMEOUT_HOURS)
        already_visited = SiteView.objects.filter(
            session_key=session_key,
            created__gte=cutoff,
        ).exists()

        if already_visited:
            # Уже считали — не создаём новую запись
            return None

        # Первый визит в этой сессии — сохраняем
        try:
            ip = get_client_ip(request)
            geo = get_city_by_ip(ip)

            SiteView.objects.create(
                path=path,
                user=request.user if request.user.is_authenticated else None,
                session_key=session_key or '',
                ip_address=ip or None,
                city=geo['city'],
                region=geo['region'],
                country=geo['country'],
                user_agent=user_agent[:500],
            )
        except Exception as e:
            logger.error(f'SiteViewMiddleware error: {e}')

        return None