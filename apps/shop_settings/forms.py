from django import forms
from .models import UnitFormula, ProductCost
from .widgets import FormulaBuilderWidget


class UnitFormulaForm(forms.ModelForm):
    class Meta:
        model = UnitFormula
        fields = ('order', 'is_total', 'name', 'expression', 'description', 'is_active')
        widgets = {
            'expression': FormulaBuilderWidget(),
        }

    def __init__(self, *args, **kwargs):
        self.unit = kwargs.pop('unit', None)
        super().__init__(*args, **kwargs)

        unit = self.unit
        if unit is None and self.instance and self.instance.pk:
            unit = self.instance.unit

        def get_variables():
            if not unit:
                return []
            return [
                {'name': v.name, 'value': str(v.value)}
                for v in unit.variables.all()
            ]

        # Защита: если поля expression вдруг нет в форме
        if 'expression' in self.fields:
            self.fields['expression'].widget.variables_getter = get_variables


class ProductCostForm(forms.ModelForm):
    class Meta:
        model = ProductCost
        fields = ('product', 'cost')
        widgets = {
            'product': forms.HiddenInput(),
        }