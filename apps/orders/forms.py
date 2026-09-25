from django import forms
from .models import Return, ReturnItem


class ReturnCreateForm(forms.ModelForm):
    """Форма создания заявки на возврат."""

    class Meta:
        model = Return
        fields = ('reason', 'comment')
        widgets = {
            'reason': forms.Select(attrs={
                'class': 'form-select',
                'required': True,
            }),
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Опишите подробнее, что не так с товаром...',
                'maxlength': 2000,
            }),
        }
        labels = {
            'reason': 'Причина возврата *',
            'comment': 'Комментарий',
        }
        help_texts = {
            'comment': 'Чем подробнее опишете — тем быстрее мы обработаем заявку.',
        }