from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('admin-panel/', include('admin_panel.urls')),
    path('accounts/', include('allauth.urls')),
    path('products/', include('apps.products.urls')),  # <-- Убедитесь, что есть /products/
    path('cart/', include('apps.cart.urls')),
    path('orders/', include('apps.orders.urls')),
    path('profile/', include('apps.accounts.urls')),
    path('', TemplateView.as_view(template_name='home.html'), name='home'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)