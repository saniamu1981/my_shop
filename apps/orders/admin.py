from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from .models import Order, OrderItem, Cart, CartItem, Return, ReturnItem, ReturnPhoto


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
    readonly_fields = ('created', 'updated', 'total_price')
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
        ('Даты', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )

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
        from django.utils import timezone
        queryset.update(status='approved', processed_at=timezone.now(), processed_by=request.user)
    mark_approved.short_description = 'Одобрить'

    def mark_rejected(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='rejected', processed_at=timezone.now(), processed_by=request.user)
    mark_rejected.short_description = 'Отклонить'

    def mark_completed(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='completed', processed_at=timezone.now(), processed_by=request.user)
    mark_completed.short_description = 'Завершить'