from .cart import CartManager

def cart_total(request):
    cart = CartManager(request)
    return {
        'cart_total': cart.get_total_price(),
        'cart_count': len(cart),
    }