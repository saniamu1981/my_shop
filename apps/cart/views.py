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
        messages.success(request, f'Товар "{product.name}" добавлен в корзину')
    else:
        cart.add(product)
        messages.success(request, f'Товар "{product.name}" добавлен в корзину')

    return redirect('cart:cart_detail')


def cart_remove(request, product_id):
    cart = CartManager(request)
    size = request.GET.get('size', '')  # Получаем размер из GET-параметров
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product_id, size=size)
    messages.success(request, f'Товар "{product.name}" удален из корзины')
    return redirect('cart:cart_detail')


def cart_update(request, product_id):
    cart = CartManager(request)
    if request.method == 'POST':
        quantity = int(request.POST.get('quantity', 1))
        size = request.POST.get('size', '')  # Получаем размер
        product = get_object_or_404(Product, id=product_id)
        if quantity > 0:
            cart.add(product, quantity, override_quantity=True, size=size)
            messages.success(request, 'Количество обновлено')
        else:
            cart.remove(product_id, size=size)
            messages.success(request, 'Товар удален из корзины')
    return redirect('cart:cart_detail')