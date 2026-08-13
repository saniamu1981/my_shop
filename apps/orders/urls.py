from django.urls import path
from . import views

app_name = 'orders'

urlpatterns = [
    path('', views.order_list, name='order_list'),
    path('create/', views.create_order, name='create_order'),
    path('buy-now/<int:product_id>/', views.buy_now, name='buy_now'),
    path('payment/<int:order_id>/', views.payment_process, name='payment_process'),
    path('success/<int:order_id>/', views.payment_success, name='payment_success'),
    path('cancel/<int:order_id>/', views.payment_cancel, name='payment_cancel'),
    path('detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('cancel-order/<int:order_id>/', views.cancel_order, name='cancel_order'),
]