from datetime import timezone

from django.db import models
from django.conf import settings
from apps.products.models import Product
from delivery.services import logger


class Order(models.Model):
    STATUS_CHOICES = (
        ('created', 'Создан'),
        ('paid', 'Оплачен'),
        ('confirmed', 'Подтверждён'),
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

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='orders',
        verbose_name='Пользователь',
    )
    first_name = models.CharField('Имя', max_length=100, blank=True, default='')
    last_name = models.CharField('Фамилия', max_length=100, blank=True, default='')
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
    delivered_at = models.DateTimeField(
        'Дата доставки',
        null=True, blank=True,
        help_text='Заполняется автоматически при смене статуса на «Доставлен».',
    )

    # Поля для интеграции с СДЭК
    cdek_order_uuid = models.CharField(
        'UUID заказа в СДЭК',
        max_length=100,
        blank=True,
        null=True,
        help_text='UUID, возвращённый СДЭК при создании заказа',
    )
    cdek_number = models.CharField(
        'Номер накладной СДЭК',
        max_length=50,
        blank=True,
        null=True,
        help_text='Номер накладной, присвоенный СДЭК',
    )
    cdek_status_code = models.CharField(
        'Код статуса СДЭК',
        max_length=20,
        blank=True,
        null=True,
    )
    cdek_status_name = models.CharField(
        'Название статуса СДЭК',
        max_length=200,
        blank=True,
        null=True,
    )

    @property
    def cdek_status_display(self):
        statuses = {
            'CREATED': 'Заказ зарегистрирован в СДЭК',
            'ACCEPTED': 'Заказ зарегистрирован в СДЭК',
            'RECEIVED_AT_SHIPMENT_WAREHOUSE': 'Посылка принята в СДЭК',
            'SENT_TO_TRANSIT': 'Посылка в пути',
            'RECEIVED_AT_TRANSIT_WAREHOUSE': 'Посылка на промежуточном складе',
            'READY_TO_TAKE_FROM_TRANSIT_WAREHOUSE': 'Готова к выдаче',
            'DELIVERED': 'Доставлена',
            'NOT_DELIVERED': 'Не доставлена',
            'RETURNED': 'Возврат',
            'RETURNED_TO_SENDER': 'Возвращена отправителю',
        }
        return statuses.get(self.cdek_status_code, self.cdek_status_name or '—')

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ('-created',)

    def __str__(self):
        user_email = self.user.email if self.user else 'удалён'
        return f'Заказ №{self.id} от {user_email}'

    def save(self, *args, **kwargs):
        # Автозаполнение delivered_at при смене статуса на 'delivered'
        if self.pk:
            try:
                old = Order.objects.get(pk=self.pk)
                if old.status != 'delivered' and self.status == 'delivered':
                    from django.utils import timezone
                    self.delivered_at = timezone.now()
            except Order.DoesNotExist:
                pass
        elif self.status == 'delivered' and not self.delivered_at:
            from django.utils import timezone
            self.delivered_at = timezone.now()

        super().save(*args, **kwargs)

    @property
    def returnable_items(self):
        """Позиции заказа, которые ещё не возвращены и доступны для возврата."""
        # id позиций, уже отправленных в активные возвраты
        returned_item_ids = set(
            self.returns.exclude(status='cancelled')
            .values_list('items__order_item_id', flat=True)
        )
        # убираем None на всякий случай
        returned_item_ids.discard(None)

        return self.items.exclude(id__in=returned_item_ids)

    @property
    def returnable_items_count(self):
        return self.returnable_items.count()

    @property
    def all_items_returned(self):
        """Все ли товары заказа уже в активном возврате."""
        return self.returnable_items_count == 0 and self.items.exists()

    @property
    def return_deadline(self):
        """Дата/время, когда истекает срок подачи заявки на возврат."""
        if not self.delivered_at:
            return None
        from apps.shop_settings.models import ShopSettings
        s = ShopSettings.get_solo()
        return self.delivered_at + s.get_return_period_timedelta()

    @property
    def can_return(self):
        if self.status != 'delivered' or not self.delivered_at:
            return False
        from django.utils import timezone
        deadline = self.return_deadline
        if not deadline or timezone.now() > deadline:
            return False
        # Есть ли ещё что возвращать?
        return self.returnable_items_count > 0

    def can_cancel(self):
        if self.status not in ['created', 'paid', 'confirmed']:
            return False
        if self.status == 'cancelled':
            return False
        # Если заказ в СДЭК и уже принят — нельзя отменить
        if self.cdek_order_uuid and self.cdek_status_code not in ('CREATED', 'ACCEPTED'):
            return False
        return True

    def cancel(self):
        if not self.can_cancel():
            return False

        # 1. Возврат денег (только если платёж succeeded)
        if self.paid and self.payment_id:
            from yookassa import Configuration, Payment
            from django.conf import settings

            Configuration.account_id = settings.YOOKASSA_SHOP_ID
            Configuration.secret_key = settings.YOOKASSA_SECRET_KEY

            try:
                payment = Payment.find_one(self.payment_id)
                if payment.status == 'succeeded':
                    from apps.orders.yookassa_refund import create_refund
                    refund = create_refund(self.payment_id, self.total_price)
                    if not refund:
                        return False
                elif payment.status == 'waiting_for_capture':
                    # Отменяем холдирование
                    import uuid
                    from yookassa import Payment as YKPayment
                    YKPayment.cancel(self.payment_id, uuid.uuid4())
                    logger.info(f'Заказ #{self.id}: холдирование отменено')
                else:
                    # Платёж в pending или canceled — возврат не нужен
                    logger.warning(
                        f'Заказ #{self.id}: платёж {self.payment_id} в статусе '
                        f'{payment.status}, возврат не требуется'
                    )
            except Exception as e:
                logger.error(f'Заказ #{self.id}: ошибка проверки платежа: {e}')
                return False

        # 2. Удаление в СДЭК
        if self.cdek_order_uuid:
            from delivery.services import CDEKService
            service = CDEKService()
            if not service.delete_order(self):
                logger.error(
                    f'Заказ #{self.id}: деньги возвращены, но заказ в СДЭК не удалён. '
                    f'Нужно удалить вручную: {self.cdek_order_uuid}'
                )

        # 3. Смена статуса
        self.status = 'cancelled'
        self.save()
        return True


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


# ============ ВОЗВРАТЫ ============

def return_photo_upload_path(instance, filename):
    """Путь для фото возврата: media/returns/<return_id>/<filename>"""
    return f'returns/{instance.return_request_id}/{filename}'


class Return(models.Model):
    """Заявка на возврат товара(ов) из заказа.
    Объединяет: причину, комментарии, позиции, фото, решение админа."""

    STATUS_CHOICES = (
        ('new', '🆕 Новая'),
        ('review', '🔍 На рассмотрении'),
        ('approved', '✅ Одобрена'),
        ('rejected', '❌ Отклонена'),
        ('completed', '🏁 Завершена'),
        ('cancelled', '🚫 Отменена клиентом'),
    )

    REASON_CHOICES = (
        ('size', 'Не подошёл размер'),
        ('quality', 'Брак / дефект'),
        ('wrong', 'Пришёл не тот товар'),
        ('damaged', 'Повреждён при доставке'),
        ('not_fit', 'Не подошёл по другим причинам'),
        ('other', 'Другое'),
    )

    # ===== Связи =====
    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name='returns',
        verbose_name='Заказ',
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='returns',
        verbose_name='Клиент',
    )

    # ===== Что хочет вернуть пользователь =====
    reason = models.CharField(
        'Причина возврата',
        max_length=20,
        choices=REASON_CHOICES,
        default='other',
    )
    comment = models.TextField('Комментарий клиента', blank=True)

    # ===== Решение администратора =====
    status = models.CharField(
        'Статус',
        max_length=20,
        choices=STATUS_CHOICES,
        default='new',
    )
    admin_comment = models.TextField('Комментарий администратора', blank=True)
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='processed_returns',
        verbose_name='Обработал',
    )
    processed_at = models.DateTimeField('Обработан', null=True, blank=True)

    # Поля для возврата денег
    refund_id = models.CharField('ID возврата в ЮKassa', max_length=100, blank=True, null=True)
    refund_status = models.CharField('Статус возврата', max_length=20, blank=True, null=True)
    refunded_at = models.DateTimeField('Дата возврата', null=True, blank=True)
    refund_amount = models.DecimalField('Сумма возврата', max_digits=10, decimal_places=2, default=0)

    # ===== Служебные =====
    created = models.DateTimeField('Создан', auto_now_add=True)
    updated = models.DateTimeField('Обновлён', auto_now=True)

    def approve(self, admin_user):
        """
        Одобряет возврат и создаёт возврат денег через ЮKassa.
        Возвращает True при успехе.
        """
        if self.status not in ('new', 'review'):
            return False

        # Считаем сумму возврата
        amount = self.total_price
        if not amount:
            logger.error(f'Возврат #{self.id}: нет позиций для возврата')
            return False

        # Создаём возврат в ЮKassa
        refund = None
        if self.order.paid and self.order.payment_id:
            from apps.orders.yookassa_refund import create_refund
            refund = create_refund(self.order.payment_id, amount)
            if not refund:
                logger.error(f'Возврат #{self.id}: не удалось создать возврат в ЮKassa')
                return False

            self.refund_id = refund.get('id')
            self.refund_status = refund.get('status')
            self.refund_amount = amount

        # Обновляем статус
        self.status = 'approved'
        self.processed_by = admin_user
        self.processed_at = timezone.now()
        self.save()

        # Push-уведомление клиенту
        try:
            from apps.accounts.utils import send_push_safe
            if self.user:
                payload = {
                    "head": "✅ Возврат одобрен",
                    "body": f"Заявка №{self.id}: {amount} ₽ вернутся на карту в течение 3–10 дней",
                    "icon": "/static/icons/icon-192x192.png",
                    "url": f"/orders/returns/{self.id}/",
                }
                send_push_safe(self.user, payload)
        except Exception as e:
            logger.error(f'Push error (return approve): {e}')

        logger.info(f'Возврат #{self.id}: одобрен, сумма {amount} ₽, refund_id={self.refund_id}')
        return True

    def complete(self, admin_user):
        """Завершает возврат (товар получен обратно)."""
        if self.status != 'approved':
            return False

        self.status = 'completed'
        self.processed_by = admin_user
        self.processed_at = timezone.now()
        self.save()

        # Возвращаем товары на склад
        for item in self.items.all():
            if item.product and item.size:
                from apps.products.models import ProductSize
                try:
                    size = ProductSize.objects.get(product=item.product, size=item.size)
                    size.quantity += item.quantity
                    size.save()
                    logger.info(
                        f'Возврат #{self.id}: товар {item.product_name} '
                        f'(размер {item.size}) возвращён на склад: +{item.quantity}'
                    )
                except ProductSize.DoesNotExist:
                    logger.warning(
                        f'Возврат #{self.id}: не найден размер {item.size} '
                        f'у товара {item.product_name}'
                    )

        return True

    class Meta:
        verbose_name = 'Возврат'
        verbose_name_plural = 'Возвраты'
        ordering = ('-created',)

    def __str__(self):
        return f'Возврат #{self.id} (заказ #{self.order_id})'

    @property
    def total_quantity(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def photos_count(self):
        return self.photos.count()


class ReturnItem(models.Model):
    """Позиция возврата — конкретный товар из заказа."""

    return_request = models.ForeignKey(
        Return,
        on_delete=models.CASCADE,
        related_name='items',
        verbose_name='Возврат',
    )
    order_item = models.ForeignKey(
        OrderItem,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='return_items',
        verbose_name='Позиция заказа',
    )
    product = models.ForeignKey(
        Product,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Товар',
    )

    # Фиксируем данные товара на момент возврата
    product_name = models.CharField('Название товара', max_length=255)
    size = models.CharField('Размер', max_length=50, blank=True)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField('Количество', default=1)

    class Meta:
        verbose_name = 'Позиция возврата'
        verbose_name_plural = 'Позиции возврата'

    def __str__(self):
        return f'{self.product_name} × {self.quantity}'

    @property
    def total_price(self):
        return self.price * self.quantity


class ReturnPhoto(models.Model):
    """Фото, приложенное к заявке на возврат."""

    return_request = models.ForeignKey(
        Return,
        on_delete=models.CASCADE,
        related_name='photos',
        verbose_name='Возврат',
    )
    image = models.ImageField('Фото', upload_to=return_photo_upload_path)
    comment = models.CharField('Подпись', max_length=255, blank=True)
    created = models.DateTimeField('Загружено', auto_now_add=True)

    class Meta:
        verbose_name = 'Фото возврата'
        verbose_name_plural = 'Фото возврата'
        ordering = ('created',)

    def __str__(self):
        return f'Фото #{self.id} к возврату #{self.return_request_id}'