from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Специфические пути (должны быть первыми)
    path('favorites/', views.favorite_list, name='favorite_list'),
    path('toggle-favorite/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),

    # Общие пути
    path('', views.product_list, name='product_list'),
    path('<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),
]