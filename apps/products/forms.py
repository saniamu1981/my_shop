from django import forms
from django.forms import inlineformset_factory
from .models import Product, ProductImage, ProductVideo, ProductSize, Category


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = (
            'category', 'name', 'slug', 'description', 'sku',
            'price', 'weight', 'available', 'image',
            # Характеристики
            'material', 'composition', 'size_on_model', 'height_on_model',
            'model_params', 'color', 'russian_size', 'country',
            'lining_material', 'fastener_type', 'sleeve', 'set_composition',
            'care_instructions',
            # Документы качества
            'quality_document', 'quality_document_name',
        )
        widgets = {
            'category': forms.Select(attrs={'class': 'form-select'}),
            'name': forms.TextInput(attrs={'class': 'form-control'}),
            'slug': forms.TextInput(attrs={'class': 'form-control', 'readonly': 'readonly'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 6}),
            'sku': forms.TextInput(attrs={'class': 'form-control'}),
            'price': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'weight': forms.NumberInput(attrs={'class': 'form-control'}),
            'available': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'image': forms.ClearableFileInput(attrs={'class': 'form-control'}),

            # Характеристики
            'material': forms.TextInput(attrs={'class': 'form-control'}),
            'composition': forms.TextInput(attrs={'class': 'form-control'}),
            'size_on_model': forms.TextInput(attrs={'class': 'form-control'}),
            'height_on_model': forms.TextInput(attrs={'class': 'form-control'}),
            'model_params': forms.TextInput(attrs={'class': 'form-control'}),
            'color': forms.TextInput(attrs={'class': 'form-control'}),
            'russian_size': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'lining_material': forms.TextInput(attrs={'class': 'form-control'}),
            'fastener_type': forms.TextInput(attrs={'class': 'form-control'}),
            'sleeve': forms.TextInput(attrs={'class': 'form-control'}),
            'set_composition': forms.TextInput(attrs={'class': 'form-control'}),
            'care_instructions': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),

            # Документы качества
            'quality_document': forms.URLInput(attrs={'class': 'form-control'}),
            'quality_document_name': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False
        self.fields['category'].empty_label = '--- Выберите категорию ---'

        # ===== «В наличии» включено по умолчанию =====
        if not self.instance.pk:  # только для новых товаров
            self.fields['available'].initial = True


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ('image', 'is_main', 'order')
        widgets = {
            'image': forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0}),
        }


class ProductVideoForm(forms.ModelForm):
    class Meta:
        model = ProductVideo
        fields = ('video', 'title', 'is_main', 'order')
        widgets = {
            'video': forms.ClearableFileInput(attrs={'class': 'form-control form-control-sm'}),
            'title': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'is_main': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'order': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0}),
        }


class ProductSizeForm(forms.ModelForm):
    class Meta:
        model = ProductSize
        fields = ('size', 'quantity', 'price')
        widgets = {
            'size': forms.TextInput(attrs={'class': 'form-control form-control-sm'}),
            'quantity': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0}),
            'price': forms.NumberInput(attrs={'class': 'form-control form-control-sm', 'min': 0, 'step': '0.01'}),
        }


# ===== Inline-формсеты =====
ProductImageFormSet = inlineformset_factory(
    Product, ProductImage,
    form=ProductImageForm,
    extra=1,
    can_delete=True,
)

ProductVideoFormSet = inlineformset_factory(
    Product, ProductVideo,
    form=ProductVideoForm,
    extra=1,
    can_delete=True,
)

ProductSizeFormSet = inlineformset_factory(
    Product, ProductSize,
    form=ProductSizeForm,
    extra=1,
    can_delete=True,
)


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ('name', 'slug', 'image')
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Например: Карнавальные костюмы',
            }),
            'slug': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'karvalnye-kostyumy',
            }),
            'image': forms.ClearableFileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*',
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['slug'].required = False