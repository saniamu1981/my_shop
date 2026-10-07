from django.contrib import admin
from django.utils.html import format_html
from solo.admin import SingletonModelAdmin

from .models import (
    ShopSettings, OrderSettings, ReturnSettings,
    UnitEconomics, UnitVariable, UnitFormula, ProductCost,
)
from .forms import UnitFormulaForm, ProductCostForm
from django.shortcuts import redirect
from django.urls import reverse


# ===== Базовый админ для singleton-настроек =====

class BaseShopSettingsAdmin(SingletonModelAdmin):
    def has_add_permission(self, request):
        return not ShopSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OrderSettings)
class OrderSettingsAdmin(BaseShopSettingsAdmin):
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


@admin.register(ShopSettings)
class ShopSettingsAdmin(BaseShopSettingsAdmin):
    def get_model_perms(self, request):
        return {}


# ============================================================
#  ЮНИТ-ЭКОНОМИКА В АДМИНКЕ
# ============================================================

class UnitVariableInline(admin.TabularInline):
    model = UnitVariable
    extra = 0
    fields = ('name', 'value', 'description')
    verbose_name = 'Переменная'
    verbose_name_plural = 'Свои переменные (налог, себестоимость и т.п.)'


class UnitFormulaInline(admin.StackedInline):
    model = UnitFormula
    form = UnitFormulaForm
    extra = 0
    fields = (
        'order',
        'is_total',
        'name',
        'expression',
        'description',
        'is_active',
        'calculated_result',
    )
    readonly_fields = ('calculated_result',)
    verbose_name = 'Формула'
    verbose_name_plural = 'Формулы'

    def calculated_result(self, obj):
        if not obj.pk:
            return '—'
        result, error = obj.calculate()
        if error:
            return format_html('<span style="color:#dc3545;">⚠ {}</span>', error)
        return format_html('<strong style="color:#28a745;">{} ₽</strong>', result)
    calculated_result.short_description = 'Результат'

    def get_formset(self, request, obj=None, **kwargs):
        """Прокидываем parent-unit в каждую форму формулы."""
        formset = super().get_formset(request, obj, **kwargs)
        FormClass = formset.form

        class FormWithUnit(FormClass):
            def __init__(self, *args, **kw):
                kw['unit'] = obj
                super().__init__(*args, **kw)

        formset.form = FormWithUnit
        return formset


class ProductCostInline(admin.TabularInline):
    model = ProductCost
    fk_name = 'unit'  # явно указываем FK на UnitEconomics
    form = ProductCostForm
    extra = 0
    fields = ('product_name_display', 'cost')
    readonly_fields = ('product_name_display',)
    verbose_name = 'Себестоимость товара'
    verbose_name_plural = 'Товары'

    def product_name_display(self, obj):
        return obj.product.name if obj.product_id else '—'
    product_name_display.short_description = 'Товар'

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('product')

    def get_formset(self, request, obj=None, **kwargs):
        if obj is not None:
            existing_ids = set(
                obj.product_costs.values_list('product_id', flat=True)
            )
            from apps.products.models import Product
            to_create = [
                ProductCost(unit=obj, product=p, cost=0)
                for p in Product.objects.all()
                if p.id not in existing_ids
            ]
            if to_create:
                ProductCost.objects.bulk_create(to_create, ignore_conflicts=True)

        return super().get_formset(request, obj, **kwargs)

        class FormWithUnit(formset.form):
            def __init__(self, *args, **kw):
                kw['unit'] = obj
                super().__init__(*args, **kw)

        formset.form = FormWithUnit
        return formset


@admin.register(UnitEconomics)
class UnitEconomicsAdmin(admin.ModelAdmin):
    list_display = ('name', 'variables_count', 'formulas_count', 'updated')
    readonly_fields = ('created', 'updated')
    inlines = [UnitVariableInline, ProductCostInline, UnitFormulaInline]

    fieldsets = (
        ('Основное', {'fields': ('name', 'description')}),
        ('Даты', {'fields': ('created', 'updated'), 'classes': ('collapse',)}),
    )

    def variables_count(self, obj):
        return obj.variables.count()
    variables_count.short_description = 'Переменных'

    def formulas_count(self, obj):
        return obj.formulas.count()
    formulas_count.short_description = 'Формул'

    def has_add_permission(self, request):
        return not UnitEconomics.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False

    # ===== Редирект со списка сразу в единственную запись =====
    def changelist_view(self, request, extra_context=None):
        obj = UnitEconomics.get_solo()
        url = reverse(
            f'admin:{self.model._meta.app_label}_{self.model._meta.model_name}_change',
            args=[obj.pk],
        )
        return redirect(url)