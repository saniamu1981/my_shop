from django.contrib import admin
from solo.admin import SingletonModelAdmin
from .models import ShopSettings, OrderSettings, ReturnSettings


# ===== Базовый админ =====
class BaseShopSettingsAdmin(SingletonModelAdmin):
    """Базовая логика singleton. НЕ скрывает раздел."""

    def has_add_permission(self, request):
        # Разрешаем "добавить" только если записи ещё нет
        # (django-solo создаёт её автоматически при первом обращении)
        return not ShopSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderSettings)
class OrderSettingsAdmin(BaseShopSettingsAdmin):
    """Раздел «Заказы» в настройках магазина."""

    fieldsets = (
        ('🛒 Заказы', {
            'fields': (),
            'description': 'Настройки заказов появятся здесь позже.',
        }),
    )

    def has_add_permission(self, request):
        return False


@admin.register(ReturnSettings)
class ReturnSettingsAdmin(BaseShopSettingsAdmin):
    """Раздел «Возвраты» в настройках магазина."""

    fieldsets = (
        ('↩️ Возвраты', {
            'fields': (
                'return_period_years',
                'return_period_months',
                'return_period_weeks',
                'return_period_days',
                'return_period_hours',
                'return_period_minutes',
            ),
            'description': (
                'Срок подачи заявки на возврат. Отсчёт начинается '
                'с момента перевода заказа в статус «Доставлен». '
                'По умолчанию — 14 дней (ЗоЗПП).'
            ),
        }),
    )

    def has_add_permission(self, request):
        return False


# ===== Скрываем базовую ShopSettings из сайдбара =====
# Регистрируем её, чтобы proxy-модели работали корректно,
# но через get_model_perms прячем из списка приложений.
@admin.register(ShopSettings)
class ShopSettingsAdmin(BaseShopSettingsAdmin):
    def get_model_perms(self, request):
        # Пустой dict = не показывать в сайдбаре
        return {}