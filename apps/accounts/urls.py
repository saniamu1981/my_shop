from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.profile, name='profile'),
    path('edit/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('offer/<int:offer_id>/', views.offer_detail, name='offer_detail'),
    path('yandex-feed.xml', views.yandex_feed, name='yandex_feed'),
    path('google-feed.xml', views.google_merchant_feed, name='google_merchant_feed'),
]