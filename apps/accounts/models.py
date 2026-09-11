from django.db import models
from django.contrib.auth.models import AbstractUser


class Offer(models.Model):
    """Версия оферты (текст, которую принимают пользователи)."""
    title = models.CharField('Название', max_length=200)
    version = models.CharField('Версия', max_length=50, blank=True, null=True,
                               help_text='Например: 1.0, 2.1. Необязательно.')
    text = models.TextField('Текст оферты')
    is_active = models.BooleanField('Активна', default=True,
                                    help_text='Активная оферта показывается пользователям.')
    created = models.DateTimeField('Создана', auto_now_add=True)
    updated = models.DateTimeField('Обновлена', auto_now=True)

    class Meta:
        verbose_name = 'Оферта'
        verbose_name_plural = 'Оферты'
        ordering = ('-is_active', '-created')

    def __str__(self):
        return f'{self.title} ({self.version})' if self.version else self.title

    def save(self, *args, **kwargs):
        # Если делаем оферту активной — снимаем активность с остальных
        if self.is_active:
            Offer.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class CustomUser(AbstractUser):
    phone = models.CharField('Телефон', max_length=20, blank=True, null=True)

    # Связь с принятой офертой
    offer_accepted = models.ForeignKey(
        Offer,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='accepted_by_users',
        verbose_name='Принятая оферта'
    )
    offer_accepted_at = models.DateTimeField(
        'Дата принятия оферты',
        null=True, blank=True
    )

    def __str__(self):
        return self.email

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'

    def has_accepted_active_offer(self):
        """Принята ли текущая активная оферта этим пользователем."""
        active = Offer.objects.filter(is_active=True).first()
        if not active:
            return True  # нет активной оферты — нечего принимать
        return self.offer_accepted_id == active.id