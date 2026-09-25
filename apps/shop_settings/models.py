from datetime import timedelta
from django.db import models
from solo.models import SingletonModel


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