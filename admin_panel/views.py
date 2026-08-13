from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from apps.products.models import Product
from apps.orders.models import Order

@staff_member_required
def dashboard(request):
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='created').count()
    
    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
    }
    return render(request, 'admin_panel/dashboard.html', context)
