from django.db import models
from django.conf import settings
from apps.products.models import Product


class Order(models.Model):
    STATUS_CHOICES = (
        ('created', 'Создан'),
        ('paid', 'Оплачен'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    )

    DELIVERY_CHOICES = (
        ('sdek', 'СДЭК'),
        ('yandex', 'Яндекс-доставка'),
        ('5post', '5 Пост'),
        ('boxberry', 'Boxberry'),
        ('courier', 'Курьерская доставка'),
        ('pickup', 'Самовывоз'),
    )

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='orders')
    first_name = models.CharField('Имя', max_length=50)
    last_name = models.CharField('Фамилия', max_length=50)
    email = models.EmailField()
    address = models.CharField('Адрес', max_length=250)
    phone = models.CharField('Телефон', max_length=20)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField('Оплачен', default=False)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='created')
    total_price = models.DecimalField('Итоговая сумма', max_digits=10, decimal_places=2, default=0)
    payment_id = models.CharField('ID платежа', max_length=100, blank=True, null=True)

    # Поля для доставки
    delivery_method = models.CharField('Способ доставки', max_length=20, choices=DELIVERY_CHOICES, blank=True,
                                       null=True)
    delivery_point_code = models.CharField('Код пункта выдачи', max_length=50, blank=True, null=True)
    delivery_point_address = models.CharField('Адрес пункта выдачи', max_length=500, blank=True, null=True)
    delivery_point_name = models.CharField('Название пункта выдачи', max_length=200, blank=True, null=True)
    delivery_price = models.DecimalField('Стоимость доставки', max_digits=10, decimal_places=2, default=0)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ('-created',)

    def __str__(self):
        return f'Заказ №{self.id} от {self.user.email}'

    def can_cancel(self):
        return self.status in ['created', 'paid'] and not self.status == 'cancelled'

    def cancel(self):
        if self.can_cancel():
            self.status = 'cancelled'
            self.save()
            return True
        return False


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField('Количество', default=1)

    class Meta:
        verbose_name = 'Товар в заказе'
        verbose_name_plural = 'Товары в заказе'

    def __str__(self):
        return f'{self.product.name} x {self.quantity}'

    def get_cost(self):
        return self.price * self.quantity


class Cart(models.Model):
    """Корзина пользователя"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='cart')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'Корзина {self.user.email}'

    def get_total_price(self):
        return sum(item.get_total_price() for item in self.items.all())

    def get_total_items(self):
        return sum(item.quantity for item in self.items.all())

    def clear(self):
        self.items.all().delete()


class CartItem(models.Model):
    """Товар в корзине"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    size = models.CharField('Размер', max_length=20, blank=True, null=True)
    quantity = models.PositiveIntegerField(default=1)
    added = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('cart', 'product', 'size')

    def __str__(self):
        return f'{self.product.name} - {self.size or "Без размера"} x {self.quantity}'

    def get_total_price(self):
        return self.product.price * self.quantity