from django.contrib import admin
from django.utils.html import format_html
from .models import CustomUser, Offer


@admin.register(Offer)
class OfferAdmin(admin.ModelAdmin):
    list_display = ('title', 'version', 'is_active', 'created', 'updated')
    list_filter = ('is_active',)
    search_fields = ('title', 'version', 'text')
    readonly_fields = ('created', 'updated')

    fieldsets = (
        ('Основное', {
            'fields': ('title', 'version', 'is_active')
        }),
        ('Текст оферты', {
            'fields': ('text',),
        }),
        ('Даты', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CustomUser)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff', 'offer_status')
    list_filter = ('is_staff', 'is_superuser', 'is_active')
    search_fields = ('email', 'first_name', 'last_name', 'phone')

    def offer_status(self, obj):
        active = Offer.objects.filter(is_active=True).first()

        if not active:
            return format_html('<span style="color:#888;">нет активной оферты</span>')

        if obj.offer_accepted_id == active.id:
            return format_html(
                '<span style="color:#28a745; font-weight:600;">✅ Принята</span>'
            )
        return format_html(
            '<span style="color:#dc3545; font-weight:600;">❌ Не принята</span>'
        )

    offer_status.short_description = 'Оферта'
    offer_status.admin_order_field = 'offer_accepted'