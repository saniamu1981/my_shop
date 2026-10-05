from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('chats/', views.chat_list, name='chat_list'),
    path('chats/<int:user_id>/', views.chat_detail, name='chat_detail'),
    path('chats/<int:user_id>/send/', views.chat_admin_send, name='chat_admin_send'),
    path('chats/<int:user_id>/messages/', views.chat_admin_messages, name='chat_admin_messages'),
    path('reset-views/', views.reset_views_counters, name='reset_views_counters'),
    path('reset-site-views/', views.reset_site_views, name='reset_site_views'),
    path('stock/', views.stock_list, name='stock_list'),
    path('stock/update/', views.stock_update, name='stock_update'),
    path('stock/update-price/', views.stock_update_price, name='stock_update_price'),
]
