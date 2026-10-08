from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.staticfiles.views import serve as staticfiles_serve
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView, RedirectView
from apps.products import views as products_views

from apps.products import feeds

from django.contrib.sitemaps.views import sitemap
from apps.products.sitemaps import ProductSitemap, CategorySitemap, StaticViewSitemap
from .views import yandex_verify

sitemaps = {
    'products': ProductSitemap,
    'categories': CategorySitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-panel/', include('admin_panel.urls')),
    path('accounts/', include('allauth.urls')),
    path('products/', include('apps.products.urls')),
    path('cart/', include('apps.cart.urls')),
    path('orders/', include('apps.orders.urls')),
    path('profile/', include('apps.accounts.urls')),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('delivery/', include('delivery.urls')),
    path('feed.yml', feeds.yml_feed, name='yml_feed'),

    # robots.txt
    path('robots.txt', TemplateView.as_view(
        template_name='robots.txt',
        content_type='text/plain'
    ), name='robots_file'),

    # favicon.ico → простой редирект на статический файл
    path('favicon.ico', RedirectView.as_view(
        url='/static/favicon.ico',   # ← ПРОСТАЯ СТРОКА, без static(), без path()
        permanent=True
    ), name='favicon'),

    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('webpush/', include('webpush.urls')),
    path('zbWxDvr6uVru67mynf3g59z.txt', yandex_verify),

    # Свой service worker ПЕРЕД pwa.urls — он перекроет встроенный
    path('serviceworker.js', products_views.service_worker, name='pwa_service_worker'),

    # === PWA: manifest.json + offline/ + serviceworker.js ===
    # pwa.urls сам регистрирует:
    #   /manifest.json
    #   /serviceworker.js
    #   /offline/
    path('', include('pwa.urls')),

    # === Webpush service worker (отдельный URL, НЕ /serviceworker.js) ===
    re_path(
        r'^webpush/serviceworker\.js$',
        staticfiles_serve,
        {'path': 'webpush/webpush_serviceworker.js'},
    ),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)