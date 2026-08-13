from decimal import Decimal
from django.conf import settings
from django.db import models
from apps.products.models import Product
from apps.orders.models import Cart as CartModel, CartItem


class CartManager:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        self.user = request.user if request.user.is_authenticated else None

        if self.user:
            self.db_cart, created = CartModel.objects.get_or_create(user=self.user)
            if self.session.get(settings.CART_SESSION_ID):
                self._merge_session_to_db()
        else:
            cart = self.session.get(settings.CART_SESSION_ID)
            if not cart:
                cart = self.session[settings.CART_SESSION_ID] = {}
            self.cart = cart

    def _merge_session_to_db(self):
        session_cart = self.session.get(settings.CART_SESSION_ID, {})
        if session_cart:
            for product_id, item_data in session_cart.items():
                try:
                    product = Product.objects.get(id=int(product_id))
                    size = item_data.get('size', '')
                    cart_item, created = CartItem.objects.get_or_create(
                        cart=self.db_cart,
                        product=product,
                        size=size,
                        defaults={'quantity': item_data['quantity']}
                    )
                    if not created:
                        cart_item.quantity += item_data['quantity']
                        cart_item.save()
                except Product.DoesNotExist:
                    pass
            self.session[settings.CART_SESSION_ID] = {}
            self.session.modified = True

    def is_empty(self):
        if self.user:
            return self.db_cart.items.count() == 0
        return len(self.cart) == 0

    def add(self, product, quantity=1, override_quantity=False, size=None):
        product_id = str(product.id)

        if self.user:
            # Если размер не указан, ищем существующий товар без размера
            if size is None or size == '':
                # Проверяем, есть ли товар без размера
                cart_item = CartItem.objects.filter(
                    cart=self.db_cart,
                    product=product,
                    size__isnull=True
                ).first()
                if cart_item:
                    if override_quantity:
                        cart_item.quantity = quantity
                    else:
                        cart_item.quantity += quantity
                    cart_item.save()
                    return
                else:
                    # Создаем новый с пустым размером
                    cart_item = CartItem.objects.create(
                        cart=self.db_cart,
                        product=product,
                        size='',
                        quantity=quantity
                    )
                    return

            # Ищем товар с конкретным размером
            cart_item, created = CartItem.objects.get_or_create(
                cart=self.db_cart,
                product=product,
                size=size,
                defaults={'quantity': quantity}
            )
            if not created:
                if override_quantity:
                    cart_item.quantity = quantity
                else:
                    cart_item.quantity += quantity
                cart_item.save()
        else:
            if product_id not in self.cart:
                self.cart[product_id] = {'quantity': 0, 'price': str(product.price), 'size': size}
            else:
                # Проверяем, совпадает ли размер
                existing_size = self.cart[product_id].get('size')
                if existing_size != size:
                    # Если размер другой, создаем новый ключ с размером
                    new_key = f"{product_id}_{size}"
                    if new_key not in self.cart:
                        self.cart[new_key] = {'quantity': 0, 'price': str(product.price), 'size': size}
                    if override_quantity:
                        self.cart[new_key]['quantity'] = quantity
                    else:
                        self.cart[new_key]['quantity'] += quantity
                    self.save()
                    return

            if override_quantity:
                self.cart[product_id]['quantity'] = quantity
            else:
                self.cart[product_id]['quantity'] += quantity
            self.save()

    def remove(self, product_id, size=None):
        product_id = str(product_id)

        if self.user:
            try:
                # Если размер указан, удаляем конкретный товар с этим размером
                if size:
                    cart_item = CartItem.objects.get(cart=self.db_cart, product_id=product_id, size=size)
                    cart_item.delete()
                else:
                    # Если размер не указан, удаляем все товары с этим product_id
                    CartItem.objects.filter(cart=self.db_cart, product_id=product_id).delete()
            except CartItem.DoesNotExist:
                pass
        else:
            if product_id in self.cart:
                del self.cart[product_id]
                self.save()

    def save(self):
        if not self.user:
            self.session.modified = True

    def __iter__(self):
        if self.user:
            items = self.db_cart.items.select_related('product').all()
            for item in items:
                yield {
                    'product': item.product,
                    'size': item.size,
                    'quantity': item.quantity,
                    'price': str(item.product.price),
                    'total_price': item.product.price * item.quantity
                }
        else:
            product_ids = self.cart.keys()
            products = Product.objects.filter(id__in=product_ids)
            cart = self.cart.copy()
            for product in products:
                for key, item in cart.items():
                    if str(product.id) in key or str(product.id) == key:
                        item['product'] = product
                        item['total_price'] = Decimal(item['price']) * item['quantity']
                        yield item

    def __len__(self):
        if self.user:
            return self.db_cart.items.aggregate(total=models.Sum('quantity'))['total'] or 0
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        if self.user:
            return self.db_cart.get_total_price()
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def clear(self):
        if self.user:
            self.db_cart.clear()
        else:
            del self.session[settings.CART_SESSION_ID]
            self.save()