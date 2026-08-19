from django.db import models

class DeliveryPoint(models.Model):
    """Кэш пунктов выдачи СДЭК"""
    code = models.CharField('Код', max_length=50, unique=True)
    name = models.CharField('Название', max_length=200)
    address = models.CharField('Адрес', max_length=500)
    city = models.CharField('Город', max_length=100)
    city_code = models.CharField('Код города', max_length=20)
    latitude = models.FloatField('Широта', null=True, blank=True)
    longitude = models.FloatField('Долгота', null=True, blank=True)
    phone = models.CharField('Телефон', max_length=20, blank=True)
    work_time = models.CharField('Время работы', max_length=200, blank=True)
    is_active = models.BooleanField('Активен', default=True)
    updated = models.DateTimeField(auto_now=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Пункт выдачи'
        verbose_name_plural = 'Пункты выдачи'
        ordering = ('city', 'name')

    def __str__(self):
        return f'{self.name} - {self.address}'