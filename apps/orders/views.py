import stripe
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Order, OrderItem
from apps.cart.cart import CartManager
from apps.products.models import Product

stripe.api_key = settings.STRIPE_SECRET_KEY


@login_required
def order_list(request):
    """Список заказов пользователя"""
    orders = Order.objects.filter(user=request.user).order_by('-created')
    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    return render(request, 'orders/order_list.html', {'orders': orders})


@login_required
def create_order(request):
    cart = CartManager(request)

    # Используем метод is_empty() вместо проверки cart.cart
    if cart.is_empty():
        messages.warning(request, 'Корзина пуста')
        return redirect('products:product_list')

    if request.method == 'POST':
        order = Order.objects.create(
            user=request.user,
            first_name=request.POST.get('first_name'),
            last_name=request.POST.get('last_name'),
            email=request.POST.get('email'),
            address=request.POST.get('address'),
            phone=request.POST.get('phone'),
            total_price=cart.get_total_price()
        )

        for item in cart:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                price=item['price'],
                quantity=item['quantity']
            )

        cart.clear()
        messages.success(request, f'Заказ №{order.id} успешно создан')
        return redirect('orders:payment_process', order_id=order.id)

    return render(request, 'orders/order_create.html', {'cart': cart})


@login_required
def payment_process(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.paid:
        messages.info(request, 'Заказ уже оплачен')
        return redirect('orders:order_detail', order_id=order.id)

    if order.status == 'cancelled':
        messages.error(request, 'Этот заказ был отменен')
        return redirect('orders:order_detail', order_id=order.id)

    try:
        session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': f'Заказ №{order.id}',
                    },
                    'unit_amount': int(order.total_price * 100),
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=request.build_absolute_uri(
                reverse('orders:payment_success', args=[order.id])
            ),
            cancel_url=request.build_absolute_uri(
                reverse('orders:payment_cancel', args=[order.id])
            ),
            metadata={
                'order_id': str(order.id),
            }
        )

        order.payment_id = session.id
        order.save()

        return redirect(session.url, 303)
    except stripe.error.StripeError as e:
        messages.error(request, f'Ошибка оплаты: {str(e)}')
        return redirect('orders:order_detail', order_id=order.id)


@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.paid = True
    order.status = 'paid'
    order.save()
    messages.success(request, f'Заказ №{order.id} успешно оплачен!')
    return render(request, 'orders/payment_success.html', {'order': order})


@login_required
def payment_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    messages.warning(request, 'Платеж был отменен')
    return render(request, 'orders/payment_cancel.html', {'order': order})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
def cancel_order(request, order_id):
    """Отмена заказа"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        if order.can_cancel():
            order.cancel()
            messages.success(request, f'Заказ №{order.id} успешно отменен')
        else:
            messages.error(request, 'Этот заказ нельзя отменить')

        return redirect('orders:order_detail', order_id=order.id)

    return redirect('orders:order_detail', order_id=order.id)


@login_required
def buy_now(request, product_id):
    """Быстрая покупка одного товара"""
    product = get_object_or_404(Product, id=product_id, available=True)

    if request.method == 'POST':
        # Создаем заказ для одного товара
        order = Order.objects.create(
            user=request.user,
            first_name=request.user.first_name or 'Покупатель',
            last_name=request.user.last_name or '',
            email=request.user.email,
            address='Адрес не указан',
            phone=request.user.phone if hasattr(request.user, 'phone') else 'Не указан',
            total_price=product.price
        )

        # Добавляем товар в заказ
        OrderItem.objects.create(
            order=order,
            product=product,
            price=product.price,
            quantity=1
        )

        messages.success(request, f'Заказ №{order.id} успешно создан для товара "{product.name}"')
        return redirect('orders:payment_process', order_id=order.id)

    return redirect('products:product_detail', category_slug=product.category.slug, product_slug=product.slug)