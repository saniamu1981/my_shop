from django.contrib import admin
from django.urls import path, include, re_path
from django.contrib.staticfiles.views import serve as staticfiles_serve
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

from apps.products import feeds

from django.contrib.sitemaps.views import sitemap
from apps.products.sitemaps import ProductSitemap, CategorySitemap, StaticViewSitemap

# Словарь, связывающий "секции" с классами Sitemap
sitemaps = {
    'products': ProductSitemap,
    'categories': CategorySitemap,
    'static': StaticViewSitemap,
}

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-panel/', include('admin_panel.urls')),
    path('accounts/', include('allauth.urls')),
    path('products/', include('apps.products.urls')),  # <-- Убедитесь, что есть /products/
    path('cart/', include('apps.cart.urls')),
    path('orders/', include('apps.orders.urls')),
    path('profile/', include('apps.accounts.urls')),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
    path('delivery/', include('delivery.urls')),
    path('feed.yml', feeds.yml_feed, name='yml_feed'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),
    path('webpush/', include('webpush.urls')),
    path('', include('pwa.urls')),  # ← манифест PWA

    # Service Worker должен отдаваться из корня домена
    re_path(r'^serviceworker\.js$', staticfiles_serve, {'path': 'webpush/serviceworker.js'}),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)