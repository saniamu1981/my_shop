from datetime import timedelta
from django.db import models
from solo.models import SingletonModel
from django.db.models import Sum, F


class ShopSettings(SingletonModel):
    """Единая модель всех настроек магазина (одна запись в БД)."""

    # ===== Возвраты =====
    return_period_years = models.PositiveIntegerField('Лет', default=0)
    return_period_months = models.PositiveIntegerField('Месяцев', default=0)
    return_period_weeks = models.PositiveIntegerField('Недель', default=0)
    return_period_days = models.PositiveIntegerField(
        'Дней', default=14,
        help_text='По умолчанию — 14 дней (Закон о защите прав потребителей).',
    )
    return_period_hours = models.PositiveIntegerField('Часов', default=0)
    return_period_minutes = models.PositiveIntegerField('Минут', default=0)

    # ===== Здесь позже добавим настройки заказов =====

    class Meta:
        verbose_name = 'Настройки магазина'
        verbose_name_plural = 'Настройки магазина'

    def __str__(self):
        return 'Настройки магазина'

    def get_return_period_timedelta(self):
        return timedelta(
            days=(
                self.return_period_years * 365
                + self.return_period_months * 30
                + self.return_period_weeks * 7
                + self.return_period_days
            ),
            hours=self.return_period_hours,
            minutes=self.return_period_minutes,
        )

    def get_return_period_display(self):
        parts = []
        if self.return_period_years:
            parts.append(f'{self.return_period_years} г.')
        if self.return_period_months:
            parts.append(f'{self.return_period_months} мес.')
        if self.return_period_weeks:
            parts.append(f'{self.return_period_weeks} нед.')
        if self.return_period_days:
            parts.append(f'{self.return_period_days} дн.')
        if self.return_period_hours:
            parts.append(f'{self.return_period_hours} ч.')
        if self.return_period_minutes:
            parts.append(f'{self.return_period_minutes} мин.')
        return ' '.join(parts) if parts else '0 мин.'


# ============ PROXY-МОДЕЛИ ДЛЯ АДМИНКИ ============

class OrderSettings(ShopSettings):
    """Раздел «Заказы» в настройках магазина (proxy)."""

    class Meta:
        proxy = True
        verbose_name = 'Заказы'
        verbose_name_plural = 'Заказы'


class ReturnSettings(ShopSettings):
    """Раздел «Возвраты» в настройках магазина (proxy)."""

    class Meta:
        proxy = True
        verbose_name = 'Возвраты'
        verbose_name_plural = 'Возвраты'


# ============================================================
#  ЮНИТ-ЭКОНОМИКА
# ============================================================

class UnitEconomics(models.Model):
    """Раздел «Юнит-экономика». Обычно одна запись — держит переменные и формулы."""

    name = models.CharField('Название', max_length=200, default='Юнит-экономика')
    description = models.TextField(
        'Описание', blank=True,
        help_text='Что считаем, какие допущения',
    )
    created = models.DateTimeField('Создана', auto_now_add=True)
    updated = models.DateTimeField('Обновлена', auto_now=True)

    class Meta:
        verbose_name = 'Юнит-экономика'
        verbose_name_plural = 'Юнит-экономика'

    def __str__(self):
        return self.name

    @classmethod
    def get_solo(cls):
        obj = cls.objects.first()
        if obj is None:
            obj = cls.objects.create(name='Юнит-экономика')
        return obj


class UnitVariable(models.Model):
    """Своя переменная (налог, себестоимость, CPA и т.п.)."""

    unit = models.ForeignKey(
        UnitEconomics, on_delete=models.CASCADE,
        related_name='variables', verbose_name='Юнит-экономика',
    )
    name = models.CharField(
        'Название переменной', max_length=100,
        help_text='Латиницей, без пробелов. Например: tax, cost, cpa',
    )
    value = models.DecimalField(
        'Значение', max_digits=12, decimal_places=2, default=0,
    )
    description = models.CharField('Описание', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Переменная юнит-экономики'
        verbose_name_plural = 'Переменные юнит-экономики'
        unique_together = ('unit', 'name')
        ordering = ('name',)

    def __str__(self):
        return f'{self.name} = {self.value}'


# ----- Встроенные метрики (правила) -----
# Импорты Order/Return — внутри функций, чтобы не словить циклический импорт.

def _sum_items_by_status(status):
    """Сумма (price × quantity) по всем позициям заказов с указанным статусом."""
    from apps.orders.models import OrderItem
    return (
        OrderItem.objects
        .filter(order__status=status)
        .aggregate(t=Sum(F('price') * F('quantity')))['t']
    ) or 0


def _count_items_by_status(status):
    """Суммарное количество единиц товара в заказах с указанным статусом."""
    from apps.orders.models import OrderItem
    return (
        OrderItem.objects
        .filter(order__status=status)
        .aggregate(t=Sum('quantity'))['t']
    ) or 0


# ---- Реестр встроенных метрик ----
# Генерируется автоматически по Order.STATUS_CHOICES.

def _cost_items_by_status(status):
    """Сумма себестоимостей (product.cost.cost × quantity) по позициям заказов в статусе."""
    from apps.orders.models import OrderItem
    from django.db.models import F
    return (
        OrderItem.objects
        .filter(order__status=status, product__cost__isnull=False)
        .aggregate(t=Sum(F('product__cost__cost') * F('quantity')))['t']
    ) or 0


def _build_builtin_metrics():
    from apps.orders.models import Order

    metrics = {}

    for code, label in Order.STATUS_CHOICES:
        metrics[f'sum_items_{code}'] = {
            'label': f'Сумма заказов: {label}',
            'resolver': (lambda c=code: _sum_items_by_status(c)),
        }
        metrics[f'count_items_{code}'] = {
            'label': f'Количество товаров: {label}',
            'resolver': (lambda c=code: _count_items_by_status(c)),
        }
        metrics[f'cost_items_{code}'] = {
            'label': f'Сумма себестоимостей: {label}',
            'resolver': (lambda c=code: _cost_items_by_status(c)),
        }

    return metrics


BUILTIN_METRICS = _build_builtin_metrics()


class UnitFormula(models.Model):
    """Формула из блоков: встроенные метрики, свои переменные, числа, знаки."""

    unit = models.ForeignKey(
        UnitEconomics, on_delete=models.CASCADE,
        related_name='formulas', verbose_name='Юнит-экономика',
    )
    name = models.CharField('Название формулы', max_length=200)

    # JSON-массив токенов:
    # [
    #   {"type": "metric",   "value": "sum_all_orders",  "label": "Сумма всех заказов"},
    #   {"type": "operator", "value": "*",               "label": "×"},
    #   {"type": "variable", "value": "tax",             "label": "tax"},
    # ]
    expression = models.JSONField(
        'Формула', default=list,
        help_text='Собирается из блоков в конструкторе',
    )

    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Активна', default=True)

    order = models.PositiveIntegerField(
        'Порядок показа',
        default=0,
        help_text='Меньше — выше в списке на дашборде. При равенстве — по дате создания.',
    )

    class Meta:
        verbose_name = 'Формула юнит-экономики'
        verbose_name_plural = 'Формулы юнит-экономики'
        ordering = ('order', 'pk')

    def __str__(self):
        return self.name

    # ---------- Считаем ----------

    def resolve_token_value(self, token):
        from decimal import Decimal

        t = token.get('type')
        v = token.get('value')

        if t == 'number':
            return Decimal(str(v))

        if t == 'metric':
            meta = BUILTIN_METRICS.get(v)
            if not meta:
                raise ValueError(f'Неизвестная метрика: {v}')
            return Decimal(str(meta['resolver']()))

        if t == 'variable':
            var = self.unit.variables.filter(name=v).first()
            if not var:
                raise ValueError(f'Переменная "{v}" не найдена')
            return var.value

        raise ValueError(f'Неизвестный тип токена: {t}')

    def calculate(self):
        """Считает формулу. Возвращает (result, error).

        Поддерживает операторы + - * / и скобки ( ).
        Приоритеты: * / выше, чем + -; скобки меняют порядок.
        Используется алгоритм shunting-yard → RPN → стек.
        """
        from decimal import InvalidOperation

        try:
            tokens = self.expression or []
            if not tokens:
                return None, 'Формула пуста'

            # Разрешённые операторы
            allowed_ops = {'+', '-', '*', '/'}
            parens = {'(', ')'}

            # Приоритеты операторов
            def precedence(op):
                if op == '(':
                    return 0
                if op in ('+', '-'):
                    return 1
                if op in ('*', '/'):
                    return 2
                return 0

            # Преобразуем токены в плоскую последовательность
            # значений (Decimal) и операторов (строки)
            values = []
            for tok in tokens:
                t = tok.get('type')
                v = tok.get('value')

                if t == 'operator':
                    if v not in allowed_ops and v not in parens:
                        return None, f'Недопустимый оператор: {v}'
                    values.append(v)
                elif t == 'paren':
                    if v not in parens:
                        return None, f'Недопустимая скобка: {v}'
                    values.append(v)
                else:
                    values.append(self.resolve_token_value(tok))

            # Проверка баланса скобок
            depth = 0
            for x in values:
                if x == '(':
                    depth += 1
                elif x == ')':
                    depth -= 1
                    if depth < 0:
                        return None, 'Лишняя закрывающая скобка'
            if depth != 0:
                return None, 'Не закрыта скобка'

            # Shunting-yard
            output = []
            stack = []
            for x in values:
                if isinstance(x, str):
                    if x == '(':
                        stack.append(x)
                    elif x == ')':
                        while stack and stack[-1] != '(':
                            output.append(stack.pop())
                        if not stack:
                            return None, 'Несбалансированные скобки'
                        stack.pop()  # выбрасываем '('
                    else:  # оператор
                        while (
                            stack
                            and stack[-1] != '('
                            and precedence(stack[-1]) >= precedence(x)
                        ):
                            output.append(stack.pop())
                        stack.append(x)
                else:
                    output.append(x)
            while stack:
                if stack[-1] == '(':
                    return None, 'Не закрыта скобка'
                output.append(stack.pop())

            # Считаем RPN
            st = []
            for x in output:
                if isinstance(x, str):
                    if x in parens:
                        # Скобки должны были исчезнуть на этапе shunting-yard
                        return None, 'Ошибка в формуле (скобки)'
                    if len(st) < 2:
                        return None, 'Недостаточно операндов'
                    b = st.pop()
                    a = st.pop()
                    if x == '+':
                        st.append(a + b)
                    elif x == '-':
                        st.append(a - b)
                    elif x == '*':
                        st.append(a * b)
                    elif x == '/':
                        if b == 0:
                            return None, 'Деление на ноль'
                        st.append(a / b)
                else:
                    st.append(x)

            if len(st) != 1:
                return None, 'Формула собрана неверно'
            return st[0], None

        except (InvalidOperation, ValueError) as e:
            return None, str(e)
        except Exception as e:
            return None, f'Ошибка: {e}'


class ProductCost(models.Model):
    """Себестоимость товара (для юнит-экономики)."""

    unit = models.ForeignKey(
        UnitEconomics,
        on_delete=models.CASCADE,
        related_name='product_costs',
        verbose_name='Юнит-экономика',
    )
    product = models.OneToOneField(
        'products.Product',
        on_delete=models.CASCADE,
        related_name='cost',
        verbose_name='Товар',
    )
    cost = models.DecimalField(
        'Себестоимость',
        max_digits=12,
        decimal_places=2,
        default=0,
    )
    updated = models.DateTimeField('Обновлена', auto_now=True)

    class Meta:
        verbose_name = 'Себестоимость товара'
        verbose_name_plural = 'Себестоимости товаров'
        ordering = ('product__name',)

    def __str__(self):
        return f'{self.product.name}: {self.cost}'