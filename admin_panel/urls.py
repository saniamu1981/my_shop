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
    path('city/delete-views/', views.delete_city_views, name='delete_city_views'),
    path('city/exclude/', views.exclude_city, name='exclude_city'),
    path('reviews/moderation/', views.review_moderation, name='review_moderation'),
    path('reviews/<int:review_id>/approve/', views.review_approve, name='review_approve'),
    path('reviews/<int:review_id>/reject/', views.review_reject, name='review_reject'),
    path('unit-economics/', views.unit_economics_page, name='unit_economics'),
    path('unit/variable/save/', views.unit_variable_save, name='unit_variable_save'),
    path('unit/variable/delete/', views.unit_variable_delete, name='unit_variable_delete'),
    path('unit/cost/save/', views.unit_cost_save, name='unit_cost_save'),
    path('unit/formula/save/', views.unit_formula_save, name='unit_formula_save'),
    path('unit/formula/delete/', views.unit_formula_delete, name='unit_formula_delete'),
]
