from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.products.models import Product
from .cart import CartManager


def cart_detail(request):
    cart = CartManager(request)

    # Пользователь пришёл в корзину — сбрасываем «быструю покупку»
    if 'buy_now' in request.session:
        request.session.pop('buy_now', None)
        request.session.modified = True

    return render(request, 'cart/cart_detail.html', {'cart': cart})


def cart_add(request, product_id):
    cart = CartManager(request)
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        size = request.POST.get('size', '')

        print(f"[DEBUG] product={product.name}, size={repr(size)}, quantity={quantity}")

        # ===== Проверка остатков =====
        available = cart.get_available_quantity(product, size)
        print(f"[DEBUG] available={available}")

        if available is not None:
            # У товара есть размеры — проверяем остаток
            if available <= 0:
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': 'Товар закончился',
                        'message': f'Размер {size} закончился',
                    }, status=400)
                messages.error(request, f'Размер {size} закончился')
                return redirect('cart:cart_detail')

            # Проверяем, сколько уже в корзине
            current_in_cart = 0
            for item in cart:
                if item['product'].id == product.id and item.get('size') == size:
                    current_in_cart = item['quantity']
                    break

            if current_in_cart + quantity > available:
                max_can_add = available - current_in_cart
                if max_can_add <= 0:
                    error_msg = f'В корзине уже максимум ({available} шт.)'
                else:
                    error_msg = f'Доступно только {available} шт. Можно добавить ещё {max_can_add} шт.'

                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': 'Недостаточно товара',
                        'message': error_msg,
                    }, status=400)
                messages.error(request, error_msg)
                return redirect('cart:cart_detail')

        cart.add(product, quantity, size=size)
        message = f'Товар "{product.name}" добавлен в корзину'
    else:
        cart.add(product)
        message = f'Товар "{product.name}" добавлен в корзину'

    # Если AJAX — отдаём JSON с актуальным количеством
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        # Предполагаем, что CartManager умеет len() или есть get_total_quantity()
        # Подставьте метод, который возвращает суммарное количество товаров
        try:
            cart_count = len(cart)
        except TypeError:
            cart_count = sum(item['quantity'] for item in cart)

        return JsonResponse({
            'success': True,
            'message': message,
            'cart_count': cart_count,
        })

    messages.success(request, message)
    return redirect('cart:cart_detail')


def cart_remove(request, product_id):
    cart = CartManager(request)
    size = request.GET.get('size', '')
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product_id, size=size)

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        try:
            cart_count = len(cart)
        except TypeError:
            cart_count = sum(item['quantity'] for item in cart)
        return JsonResponse({'success': True, 'cart_count': cart_count})

    messages.success(request, f'Товар "{product.name}" удален из корзины')
    return redirect('cart:cart_detail')


def cart_update(request, product_id):
    cart = CartManager(request)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        size = request.POST.get('size', '')
        product = get_object_or_404(Product, id=product_id)

        # ===== Проверка остатков =====
        if quantity > 0:
            available = cart.get_available_quantity(product, size)

            if available is not None and quantity > available:
                error_msg = f'Доступно только {available} шт.'
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({
                        'success': False,
                        'error': 'Недостаточно товара',
                        'message': error_msg,
                    }, status=400)
                messages.error(request, error_msg)
                return redirect('cart:cart_detail')

            cart.add(product, quantity, override_quantity=True, size=size)
        else:
            cart.remove(product_id, size=size)

        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            try:
                cart_count = len(cart)
            except TypeError:
                cart_count = sum(item['quantity'] for item in cart)
            return JsonResponse({'success': True, 'cart_count': cart_count})

    return redirect('cart:cart_detail')