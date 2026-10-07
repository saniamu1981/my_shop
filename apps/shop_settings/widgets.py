import json
from django import forms


def _metric_group(code):
    """Определяем группу метрики по её коду."""
    # ===== Заказы =====
    if code.startswith('sum_items_'):
        return 'Заказы: Сумма'
    if code.startswith('count_items_'):
        return 'Заказы: Количество товаров'
    if code.startswith('cost_items_'):
        return 'Заказы: Себестоимости'

    # ===== Возвраты =====
    if code.startswith('return_refund_'):
        return 'Возвраты: Сумма (деньги)'
    if code.startswith('return_items_'):
        return 'Возвраты: Сумма (товары)'
    if code.startswith('return_count_'):
        return 'Возвраты: Количество товаров'
    if code.startswith('return_cost_'):
        return 'Возвраты: Себестоимости'

    return 'Прочее'


class FormulaBuilderWidget(forms.Widget):
    """Виджет-конструктор для поля expression.

    Слева — доступные блоки: встроенные метрики, свои переменные, числа, знаки.
    Справа — собранная формула. Всё пишется в скрытый input как JSON.
    """

    template_name = 'admin/shop_settings/widgets/formula_builder.html'

    class Media:
        css = {'all': ('admin/shop_settings/formula_builder_v2.css',)}
        js = ('admin/shop_settings/formula_builder_v2.js',)

    def __init__(self, variables_getter=None, attrs=None):
        super().__init__(attrs)
        self.variables_getter = variables_getter

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        # Значение — либо строка JSON, либо список
        if isinstance(value, str):
            try:
                value = json.loads(value) if value else []
            except Exception:
                value = []
        if not value:
            value = []

        # Свои переменные — через колбэк (передаётся из формы)
        variables = []
        if self.variables_getter:
            try:
                variables = list(self.variables_getter())
            except Exception:
                variables = []

        # Встроенные метрики — берём из модели
        from .models import BUILTIN_METRICS
        builtin = [
            {
                'code': code,
                'label': meta['label'],
                'group': _metric_group(code),
            }
            for code, meta in BUILTIN_METRICS.items()
        ]

        context['widget']['value_json'] = json.dumps(value)
        context['widget']['expression'] = value
        context['widget']['variables'] = variables
        context['widget']['builtin_metrics'] = builtin
        return context