from django.urls import path
from . import views

app_name = 'accounts'

urlpatterns = [
    path('', views.profile, name='profile'),
    path('edit/', views.edit_profile, name='edit_profile'),
    path('change-password/', views.change_password, name='change_password'),
    path('offer/<int:offer_id>/', views.offer_detail, name='offer_detail'),
    path('chat/', views.chat, name='chat'),
    path('chat/send/', views.chat_send, name='chat_send'),
    path('chat/messages/', views.chat_messages, name='chat_messages'),
    path('profile/delete/', views.profile_delete, name='profile_delete'),
]