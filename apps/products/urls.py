from django.urls import path
from . import views

app_name = 'products'

urlpatterns = [
    # Специфические пути (должны быть первыми)
    path('favorites/', views.favorite_list, name='favorite_list'),
    path('toggle-favorite/<int:product_id>/', views.toggle_favorite, name='toggle_favorite'),
    path('reviews/<int:product_id>/', views.get_product_reviews, name='get_product_reviews'),
    path('edit-review/<int:product_id>/', views.edit_review, name='edit_review'),
    path('delete-review/<int:review_id>/', views.delete_review, name='delete_review'),

    # Общие пути
    path('', views.product_list, name='product_list'),
    path('<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('<slug:category_slug>/<slug:product_slug>/', views.product_detail, name='product_detail'),
]