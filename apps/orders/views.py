import stripe
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from .models import Order, OrderItem
from apps.cart.cart import CartManager
from apps.products.models import Product, Review

stripe.api_key = settings.STRIPE_SECRET_KEY


# apps/orders/views.py

@login_required
def order_list(request):
    """Список заказов пользователя"""
    orders = Order.objects.filter(user=request.user).order_by('-created')

    # Добавляем информацию об отзывах для каждого товара в заказе
    for order in orders:
        for item in order.items.all():
            # Проверяем, есть ли отзыв на этот товар от ЭТОГО пользователя
            has_review = Review.objects.filter(
                product=item.product,
                user=request.user  # <-- Важно: проверяем конкретного пользователя
            ).exists()
            item.has_review = has_review
            # Отладка
            print(f"Order {order.id}, Product {item.product.id}, User {request.user.email}: has_review = {has_review}")

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
        size = request.POST.get('size', '')
        delivery_method = request.POST.get('delivery_method', '')
        delivery_point = request.POST.get('delivery_point', '{}')

        try:
            import json
            point_data = json.loads(delivery_point) if delivery_point else {}
        except:
            point_data = {}

        # Получаем телефон пользователя, если есть
        user_phone = ''
        if hasattr(request.user, 'phone') and request.user.phone:
            user_phone = request.user.phone
        elif hasattr(request.user, 'profile') and hasattr(request.user.profile, 'phone'):
            user_phone = request.user.profile.phone

        # Если телефона нет, используем заглушку
        if not user_phone:
            user_phone = 'Не указан'

        order = Order.objects.create(
            user=request.user,
            first_name=request.user.first_name or 'Покупатель',
            last_name=request.user.last_name or '',
            email=request.user.email,
            address=point_data.get('address', 'Адрес не указан'),
            phone=user_phone,  # <-- Важно: передаем телефон
            total_price=product.price,
            delivery_method=delivery_method,
            delivery_point_code=point_data.get('code', ''),
            delivery_point_name=point_data.get('name', ''),
            delivery_point_address=point_data.get('address', ''),
        )

        OrderItem.objects.create(
            order=order,
            product=product,
            price=product.price,
            quantity=1
        )

        messages.success(request, f'Заказ №{order.id} успешно создан для товара "{product.name}"')
        return redirect('orders:payment_process', order_id=order.id)

    return redirect('products:product_detail', category_slug=product.category.slug, product_slug=product.slug)

@login_required
def add_review(request):
    """
    Страница добавления отзыва на товары из доставленного заказа
    """
    order_id = request.GET.get('order_id')

    if not order_id:
        messages.error(request, 'Заказ не указан')
        return redirect('orders:order_list')

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Проверяем, что заказ доставлен
    if order.status != 'delivered':
        messages.error(request, 'Отзыв можно оставить только для доставленных заказов')
        return redirect('orders:order_list')

    # Проверяем, есть ли уже отзывы на товары из этого заказа
    existing_reviews = Review.objects.filter(order=order, user=request.user)
    reviewed_product_ids = existing_reviews.values_list('product_id', flat=True)

    # Получаем товары из заказа, на которые еще нет отзывов
    items = order.items.all()
    available_products = []
    for item in items:
        if item.product.id not in reviewed_product_ids:
            available_products.append(item.product)

    if not available_products:
        messages.info(request, 'Вы уже оставили отзывы на все товары из этого заказа')
        return redirect('orders:order_list')

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if not product_id or not rating:
            messages.error(request, 'Заполните все обязательные поля')
            return redirect(f'/orders/add-review/?order_id={order_id}')

        product = get_object_or_404(Product, id=product_id)

        # Проверяем, что товар есть в заказе
        if not order.items.filter(product_id=product_id).exists():
            messages.error(request, 'Товар не найден в заказе')
            return redirect('orders:order_list')

        # Проверяем, что отзыв еще не оставлен
        if Review.objects.filter(product=product, user=request.user, order=order).exists():
            messages.warning(request, 'Отзыв на этот товар уже оставлен')
            return redirect(f'/orders/add-review/?order_id={order_id}')

        Review.objects.create(
            product=product,
            user=request.user,
            order=order,
            rating=int(rating),
            comment=comment
        )

        messages.success(request, f'Спасибо за отзыв на "{product.name}"!')

        # Проверяем, остались ли еще товары без отзывов
        remaining_items = order.items.exclude(product_id=product_id)
        remaining_products = []
        for item in remaining_items:
            if item.product.id not in reviewed_product_ids:
                remaining_products.append(item.product)

        if remaining_products:
            return redirect(f'/orders/add-review/?order_id={order_id}')
        else:
            return redirect('orders:order_list')

    context = {
        'order': order,
        'available_products': available_products,
        'existing_reviews': existing_reviews,
    }
    return render(request, 'orders/add_review.html', context)