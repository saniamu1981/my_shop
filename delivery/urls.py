from django.urls import path
from . import views

urlpatterns = [
    # Адресные справочники
    path('api/regions/', views.get_regions, name='regions'),
    path('api/cities/', views.get_cities_by_region, name='cities'),
    path('api/districts/', views.get_districts_by_city, name='districts'),

    # CDEK
    path('api/cdek-points/', views.get_cdek_points_by_location, name='cdek_points'),

    # Тестовые эндпоинты
    path('api/test-cdek/', views.test_cdek_connection, name='test_cdek'),
]