from django import forms
from allauth.account.forms import SignupForm
from django.utils import timezone


class CustomSignupForm(SignupForm):
    """
    Переопределённая форма регистрации:
    - убираем username (у вас вход по email)
    - добавляем чекбокс согласия на обработку ПД
    """
    personal_data_consent = forms.BooleanField(
        label='Я согласен на обработку персональных данных',
        required=True,
        error_messages={
            'required': 'Необходимо согласие на обработку персональных данных.',
        },
    )

    def save(self, request):
        user = super().save(request)
        user.personal_data_consent = True
        user.personal_data_consent_at = timezone.now()
        user.save(update_fields=['personal_data_consent', 'personal_data_consent_at'])
        return user