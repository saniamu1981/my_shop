from django.contrib import admin
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from django.utils.html import format_html
from django.urls import reverse
from .models import Order, OrderItem, Cart, CartItem, Return, ReturnItem, ReturnPhoto
from delivery.services import CDEKService


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ('product',)
    extra = 0
    readonly_fields = ('product', 'price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'user', 'first_name', 'last_name',
        'total_price', 'paid', 'status',
        'delivery_method_display', 'created',
    )
    list_filter = ('paid', 'status', 'delivery_method', 'created')
    list_editable = ('status',)
    search_fields = ('user__email', 'first_name', 'last_name', 'phone')
    readonly_fields = ('created', 'updated', 'total_price', 'cdek_order_uuid', 'cdek_number', 'cdek_status_code', 'cdek_status_name', 'cdek_buttons')
    inlines = [OrderItemInline]
    actions = ['mark_as_paid', 'mark_as_confirmed', 'mark_as_shipped', 'mark_as_delivered']

    fieldsets = (
        ('Информация о заказе', {
            'fields': ('user', 'first_name', 'last_name', 'email', 'phone', 'address')
        }),
        ('Статус и оплата', {
            'fields': ('status', 'paid', 'total_price')
        }),
        ('Доставка', {
            'fields': (
                'delivery_method',
                'delivery_price',
                'delivery_point_name',
                'delivery_point_address',
                'delivery_point_code',
            ),
            'description': 'Информация о выбранном способе доставки и пункте выдачи.',
        }),
        ('СДЭК', {
            'fields': (
                'cdek_buttons',
                'cdek_order_uuid',
                'cdek_number',
                'cdek_status_code',
                'cdek_status_name',
            ),
            'classes': ('collapse',),
            'description': 'Заполняется автоматически при создании заказа в СДЭК.',
        }),
        ('Даты', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:order_id>/create-cdek/', self.admin_site.admin_view(self.create_cdek_view), name='order-create-cdek'),
            path('<int:order_id>/sync-cdek/', self.admin_site.admin_view(self.sync_cdek_view), name='order-sync-cdek'),
        ]
        return custom_urls + urls

    def create_cdek_view(self, request, order_id):
        from .models import Order
        order = Order.objects.get(id=order_id)

        if order.cdek_order_uuid:
            self.message_user(
                request,
                f'Заказ уже создан в СДЭК (накладная {order.cdek_number})',
                level=messages.WARNING,
            )
            return redirect(request.META.get('HTTP_REFERER', '/admin/'))

        service = CDEKService()
        result = service.create_order(order)

        if result:
            self.message_user(
                request,
                f'Заказ создан в СДЭК: {order.cdek_number}',
                level=messages.SUCCESS,
            )
        else:
            self.message_user(
                request,
                'Ошибка создания заказа в СДЭК. Проверьте логи.',
                level=messages.ERROR,
            )
        return redirect(request.META.get('HTTP_REFERER', '/admin/'))

    def sync_cdek_view(self, request, order_id):
        from .models import Order
        order = Order.objects.get(id=order_id)

        if not order.cdek_order_uuid:
            self.message_user(
                request,
                'Заказ ещё не создан в СДЭК',
                level=messages.WARNING,
            )
            return redirect(request.META.get('HTTP_REFERER', '/admin/'))

        service = CDEKService()
        service.sync_order_status(order)

        self.message_user(
            request,
            f'Статус обновлён: {order.status} — {order.cdek_status_name or "—"}',
            level=messages.SUCCESS,
        )
        return redirect(request.META.get('HTTP_REFERER', '/admin/'))

    def cdek_buttons(self, obj):
        if not obj.pk:
            return '—'
        create_url = reverse('admin:order-create-cdek', args=[obj.pk])
        sync_url = reverse('admin:order-sync-cdek', args=[obj.pk])
        return format_html(
            '<a class="button" href="{}" style="margin-right: 8px;">📦 Создать в СДЭК</a>'
            '<a class="button" href="{}">🔄 Синхронизировать статус</a>',
            create_url, sync_url,
        )
    cdek_buttons.short_description = 'Действия СДЭК'

    def mark_as_confirmed(self, request, queryset):
        queryset.update(status='confirmed')

    mark_as_confirmed.short_description = 'Отметить как подтверждённые'

    def mark_as_paid(self, request, queryset):
        queryset.update(paid=True, status='paid')

    mark_as_paid.short_description = 'Отметить как оплаченные'

    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')

    mark_as_shipped.short_description = 'Отметить как отправленные'

    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered')

    mark_as_delivered.short_description = 'Отметить как доставленные'

    @admin.display(description='Доставка')
    def delivery_method_display(self, obj):
        if not obj.delivery_method:
            return '—'
        # get_delivery_method_display возвращает человекочитаемое название
        return obj.get_delivery_method_display()


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'created', 'updated', 'total_items', 'total_price')
    list_filter = ('created', 'updated')
    search_fields = ('user__email',)

    def total_items(self, obj):
        return obj.get_total_items()

    total_items.short_description = 'Товаров'

    def total_price(self, obj):
        return f'{obj.get_total_price()} ₽'

    total_price.short_description = 'Сумма'


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ('cart', 'product', 'quantity', 'total_price')
    list_filter = ('cart__user',)
    search_fields = ('product__name', 'cart__user__email')

    def total_price(self, obj):
        return f'{obj.get_total_price()} ₽'

    total_price.short_description = 'Сумма'


class ReturnItemInline(admin.TabularInline):
    model = ReturnItem
    extra = 0
    raw_id_fields = ('order_item', 'product')
    readonly_fields = ('total_price_display',)
    fields = ('product', 'product_name', 'size', 'price', 'quantity', 'total_price_display')

    def total_price_display(self, obj):
        if obj.pk:
            return f'{obj.total_price} ₽'
        return '—'
    total_price_display.short_description = 'Сумма'


class ReturnPhotoInline(admin.TabularInline):
    model = ReturnPhoto
    extra = 0
    readonly_fields = ('image_preview', 'created')
    fields = ('image', 'image_preview', 'comment', 'created')

    def image_preview(self, obj):
        if obj.image:
            return format_html(
                '<a href="{0}" target="_blank">'
                '<img src="{0}" style="max-height: 80px; border-radius: 6px;" />'
                '</a>',
                obj.image.url,
            )
        return '—'
    image_preview.short_description = 'Превью'


@admin.register(Return)
class ReturnAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'order', 'user', 'reason', 'status',
        'total_quantity_display', 'total_price_display',
        'photos_count_display', 'created', 'processed_at',
    )
    list_filter = ('status', 'reason', 'created')
    search_fields = (
        'id', 'order__id',
        'user__email', 'user__first_name', 'user__last_name',
        'comment', 'admin_comment',
    )
    list_editable = ('status',)
    date_hierarchy = 'created'
    inlines = [ReturnItemInline, ReturnPhotoInline]
    readonly_fields = ('created', 'updated', 'order_link', 'user_link')
    actions = ['mark_review', 'mark_approved', 'mark_rejected', 'mark_completed']

    fieldsets = (
        ('Заявка', {
            'fields': ('order_link', 'user_link', 'reason', 'comment', 'created')
        }),
        ('Решение администратора', {
            'fields': ('status', 'admin_comment', 'processed_by', 'processed_at')
        }),
        ('Служебное', {
            'fields': ('updated',),
            'classes': ('collapse',),
        }),
    )

    def order_link(self, obj):
        if obj.pk:
            url = reverse('admin:orders_order_change', args=[obj.order_id])
            return format_html('<a href="{}">Заказ №{}</a>', url, obj.order_id)
        return '—'
    order_link.short_description = 'Заказ'

    def user_link(self, obj):
        if obj.pk:
            url = reverse('admin:accounts_customuser_change', args=[obj.user_id])
            return format_html('<a href="{}">{}</a>', url, obj.user.email)
        return '—'
    user_link.short_description = 'Клиент'

    def total_quantity_display(self, obj):
        return obj.total_quantity
    total_quantity_display.short_description = 'Кол-во'

    def total_price_display(self, obj):
        return f'{obj.total_price} ₽'
    total_price_display.short_description = 'Сумма'

    def photos_count_display(self, obj):
        return obj.photos_count
    photos_count_display.short_description = 'Фото'

    def mark_review(self, request, queryset):
        queryset.update(status='review')
    mark_review.short_description = 'Взять на рассмотрение'

    def mark_approved(self, request, queryset):
        success = 0
        failed = 0
        for ret in queryset:
            if ret.approve(request.user):
                success += 1
            else:
                failed += 1

        if success:
            self.message_user(request, f'Одобрено возвратов: {success}', level=messages.SUCCESS)
        if failed:
            self.message_user(request, f'Не удалось одобрить: {failed}', level=messages.ERROR)

    mark_approved.short_description = '✅ Одобрить'

    def mark_rejected(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='rejected', processed_at=timezone.now(), processed_by=request.user)
    mark_rejected.short_description = 'Отклонить'

    def mark_completed(self, request, queryset):
        for ret in queryset:
            ret.complete(request.user)
        self.message_user(request, f'Завершено возвратов: {queryset.count()}', level=messages.SUCCESS)

    mark_completed.short_description = '🏁 Завершить и вернуть деньги'