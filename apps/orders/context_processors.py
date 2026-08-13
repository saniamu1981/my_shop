from .models import Order

def orders_count(request):
    """Контекстный процессор для количества заказов, ожидающих оплаты"""
    if request.user.is_authenticated:
        # Считаем только неоплаченные и неотмененные заказы
        pending_orders_count = Order.objects.filter(
            user=request.user,
            paid=False
        ).exclude(
            status='cancelled'
        ).count()
        return {
            'orders_count': pending_orders_count
        }
    return {'orders_count': 0}