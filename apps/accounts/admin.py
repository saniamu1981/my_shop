from django.contrib import admin
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from django.urls import reverse

from .models import CustomUser, Offer, ChatMessage


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
    list_display = (
        'email',
        'first_name',
        'last_name',
        'is_staff',
        'personal_data_consent_display',   # ← НОВЫЙ СТОЛБЕЦ
        'offer_status',
    )
    list_filter = (
        'is_staff',
        'is_superuser',
        'is_active',
        'personal_data_consent',            # ← НОВЫЙ ФИЛЬТР
    )
    search_fields = ('email', 'first_name', 'last_name', 'phone')

    # ===== Согласие на обработку ПД =====
    @admin.display(description='Согласие на ПД', boolean=True)
    def personal_data_consent_display(self, obj):
        return obj.personal_data_consent

    # ===== Статус оферты =====
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


class ChatMessageInline(admin.TabularInline):
    """Показываем сообщения прямо в карточке пользователя."""
    model = ChatMessage
    extra = 0
    fields = ('sender', 'message', 'is_read', 'created')
    readonly_fields = ('created',)
    ordering = ('created',)
    can_delete = True
    show_change_link = True


# Дополняем UserAdmin — переопределяем, потому что выше уже зарегистрирован
UserAdmin.inlines = [ChatMessageInline]


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'user_link', 'sender', 'short_message', 'is_read', 'created')
    list_filter = ('sender', 'is_read', 'created')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'message')
    list_editable = ('is_read',)
    readonly_fields = ('created',)
    date_hierarchy = 'created'
    ordering = ('-created',)
    list_per_page = 50

    fieldsets = (
        ('Сообщение', {
            'fields': ('user', 'sender', 'message', 'is_read')
        }),
        ('Даты', {
            'fields': ('created',),
            'classes': ('collapse',)
        }),
    )

    def user_link(self, obj):
        url = reverse('admin:accounts_customuser_change', args=[obj.user_id])
        return mark_safe(f'<a href="{url}">{obj.user.email}</a>')

    user_link.short_description = 'Пользователь'
    user_link.admin_order_field = 'user__email'

    def short_message(self, obj):
        return obj.message[:80] + ('…' if len(obj.message) > 80 else '')

    short_message.short_description = 'Сообщение'

    # Массовые действия
    actions = ['mark_as_read', 'mark_as_unread']

    @admin.action(description='Отметить как прочитанные')
    def mark_as_read(self, request, queryset):
        updated = queryset.update(is_read=True)
        self.message_user(request, f'Отмечено как прочитано: {updated}')

    @admin.action(description='Отметить как непрочитанные')
    def mark_as_unread(self, request, queryset):
        updated = queryset.update(is_read=False)
        self.message_user(request, f'Отмечено как непрочитано: {updated}')