from django.urls import path
from . import views

urlpatterns = [
    # Адресные справочники
    path('api/regions/', views.get_regions, name='regions'),
    path('api/cities/', views.get_cities_by_region, name='cities'),
    path('api/districts/', views.get_districts_by_city, name='districts'),
    path('api/all-cities/', views.get_all_cities, name='all_cities'),
    path('api/cdek-all-points/', views.get_all_cdek_points, name='cdek_all_points'),

    # CDEK
    path('api/cdek-points/', views.get_cdek_points_by_location, name='cdek_points'),

    # Тестовые эндпоинты
    path('api/test-cdek/', views.test_cdek_connection, name='test_cdek'),

    # СДЭК интеграция
    path('api/cdek/orders/<int:order_id>/create/', views.create_cdek_order_view, name='cdek_create_order'),
    path('api/cdek/orders/<int:order_id>/sync/', views.sync_cdek_status_view, name='cdek_sync_order'),

    # Вебхук от СДЭК (если будете подписываться)
    path('api/cdek/webhook/', views.cdek_webhook, name='cdek_webhook'),
]