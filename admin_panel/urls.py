from django.urls import path
from . import views

app_name = 'admin_panel'

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('chats/', views.chat_list, name='chat_list'),
    path('chats/<int:user_id>/', views.chat_detail, name='chat_detail'),
    path('chats/<int:user_id>/send/', views.chat_admin_send, name='chat_admin_send'),
    path('chats/<int:user_id>/messages/', views.chat_admin_messages, name='chat_admin_messages'),
]
