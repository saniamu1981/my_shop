from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from apps.products.models import Product
from .cart import CartManager


def cart_detail(request):
    cart = CartManager(request)
    return render(request, 'cart/cart_detail.html', {'cart': cart})


def cart_add(request, product_id):
    cart = CartManager(request)
    product = get_object_or_404(Product, id=product_id)

    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        size = request.POST.get('size', '')
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
        if quantity > 0:
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