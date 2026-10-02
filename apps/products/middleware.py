from django.utils.deprecation import MiddlewareMixin
from .models import SiteView
from .utils import get_client_ip, get_city_by_ip
import logging

logger = logging.getLogger(__name__)


class SiteViewMiddleware(MiddlewareMixin):
    """Сохраняет каждый просмотр страницы сайта (только от реальных людей)."""

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
        # Пути, куда ходят только боты
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

    # Паттерны User-Agent ботов
    BOT_PATTERNS = (
        # Поисковые боты
        'bot', 'crawler', 'spider', 'slurp',
        'googlebot', 'bingbot', 'yandexbot', 'duckduckbot',
        'baiduspider', 'sogou', 'exabot', 'ia_archiver',
        'ahrefs', 'semrush', 'mj12bot', 'dotbot', 'petalbot',
        'seznam', 'screaming frog', 'seokicks',
        # Инструменты и скрипты
        'curl', 'wget', 'httpie', 'axios', 'okhttp',
        'python-requests', 'python-urllib', 'python-httpx',
        'go-http-client', 'java/', 'libwww-perl',
        'apache-httpclient', 'guzzle', 'node-fetch',
        # Сканеры уязвимостей
        'scanner', 'nikto', 'nmap', 'masscan', 'zgrab',
        'nuclei', 'sqlmap', 'dirbuster', 'gobuster',
        # Мониторинг
        'uptimerobot', 'pingdom', 'statuscake', 'newrelic',
        'datadog', 'monitis',
        # Соцсети и мессенджеры (превью ссылок)
        'facebookexternalhit', 'telegrambot', 'whatsapp',
        'twitterbot', 'linkedinbot', 'slackbot',
        'discordbot', 'skypeuripreview',
        # Прочее
        'headlesschrome', 'phantomjs', 'selenium',
        'puppeteer', 'playwright',
    )

    def process_request(self, request):
        # Пропускаем исключённые пути
        path = request.path
        if any(path.startswith(prefix) for prefix in self.EXCLUDED_PREFIXES):
            return None

        # Только GET-запросы
        if request.method != 'GET':
            return None

        # Проверка User-Agent
        user_agent = request.META.get('HTTP_USER_AGENT', '').strip()

        # Пустой User-Agent — почти наверняка бот
        if not user_agent:
            return None

        ua_lower = user_agent.lower()
        if any(pattern in ua_lower for pattern in self.BOT_PATTERNS):
            return None

        # Пропускаем админов
        if request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff):
            return None

        # Пропускаем запросы без Accept-Language (браузеры всегда его шлют)
        accept_language = request.META.get('HTTP_ACCEPT_LANGUAGE', '')
        if not accept_language:
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
                user_agent=user_agent[:500],
            )
        except Exception as e:
            logger.error(f'SiteViewMiddleware error: {e}')

        return None