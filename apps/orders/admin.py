from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, Cart, CartItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ('product',)
    extra = 0
    readonly_fields = ('product', 'price', 'quantity')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'first_name', 'last_name', 'total_price', 'paid', 'status', 'created')
    list_filter = ('paid', 'status', 'created')
    list_editable = ('status',)
    search_fields = ('user__email', 'first_name', 'last_name', 'phone')
    readonly_fields = ('created', 'updated', 'total_price')
    inlines = [OrderItemInline]
    actions = ['mark_as_paid', 'mark_as_shipped', 'mark_as_delivered']

    fieldsets = (
        ('Информация о заказе', {
            'fields': ('user', 'first_name', 'last_name', 'email', 'phone', 'address')
        }),
        ('Статус и оплата', {
            'fields': ('status', 'paid', 'total_price')
        }),
        ('Даты', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )

    def mark_as_paid(self, request, queryset):
        queryset.update(paid=True, status='paid')

    mark_as_paid.short_description = 'Отметить как оплаченные'

    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')

    mark_as_shipped.short_description = 'Отметить как отправленные'

    def mark_as_delivered(self, request, queryset):
        queryset.update(status='delivered')

    mark_as_delivered.short_description = 'Отметить как доставленные'


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