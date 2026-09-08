from django.contrib import admin
from django import forms
from django.utils.html import format_html
from .models import Category, Product, ProductImage, ProductVideo, Favorite, ProductSize


class ProductImageForm(forms.ModelForm):
    local_path = forms.CharField(
        label='Локальный путь (относительно media/)',
        required=False,
        help_text='Пример: products/kostyum_gornichnoj_rozovyj/1.jpg',
        widget=forms.TextInput(attrs={'size': 80, 'style': 'width: 100%;'})
    )

    class Meta:
        model = ProductImage
        fields = ('product', 'image', 'is_main', 'order')

    def save(self, commit=True):
        instance = super().save(commit=False)
        local_path = self.cleaned_data.get('local_path')
        if local_path and instance.image:
            # Сохраняем по локальному пути
            instance.image.name = local_path
            instance._local_path = local_path
        if commit:
            instance.save()
        return instance


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    form = ProductImageForm
    extra = 3
    fields = ('image', 'is_main', 'order', 'local_path', 'preview')
    readonly_fields = ('preview',)
    ordering = ('order',)

    def preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px;"/>', obj.image.url)
        return 'Нет фото'

    preview.short_description = 'Превью'


class ProductVideoInline(admin.TabularInline):
    model = ProductVideo
    extra = 1
    fields = ('video', 'title', 'is_main', 'order', 'preview')
    readonly_fields = ('preview',)
    ordering = ('order',)

    def preview(self, obj):
        if obj.video:
            return format_html(
                '<video width="100" height="80" controls style="max-height: 80px;">'
                '<source src="{}" type="{}">'
                '</video>',
                obj.video.url,
                obj.get_video_type()
            )
        return 'Нет видео'

    preview.short_description = 'Превью'


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'product_count')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name',)
    ordering = ('name',)

    def product_count(self, obj):
        return obj.products.count()

    product_count.short_description = 'Количество товаров'


class ProductSizeInline(admin.TabularInline):
    model = ProductSize
    extra = 3
    fields = ('size', 'quantity', 'price')
    ordering = ('size',)


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Добавляем поле для локального пути к главному изображению
        self.fields['local_path'] = forms.CharField(
            label='Локальный путь главного фото (относительно media/)',
            required=False,
            help_text='Пример: products/kostyum_gornichnoj_rozovyj/1.jpg',
            widget=forms.TextInput(attrs={'size': 80, 'style': 'width: 100%;'})
        )

    def save(self, commit=True):
        instance = super().save(commit=False)
        local_path = self.cleaned_data.get('local_path')
        if local_path and instance.image:
            instance.image.name = local_path
        if commit:
            instance.save()
        return instance


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    form = ProductForm
    list_display = ('name', 'category', 'price', 'available', 'sku', 'created')
    list_filter = ('available', 'category', 'created')
    list_editable = ('price', 'available')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description', 'sku')
    readonly_fields = ('created', 'updated')
    inlines = [ProductImageInline, ProductVideoInline, ProductSizeInline]

    fieldsets = (
        ('Основная информация', {
            'fields': ('category', 'name', 'slug', 'description', 'sku')
        }),
        ('Цена и наличие', {
            'fields': ('price', 'available')
        }),
        ('Главное изображение', {
            'fields': ('image', 'local_path')
        }),
        ('Характеристики товара', {
            'fields': (
                'material', 'composition', 'size_on_model', 'height_on_model',
                'model_params', 'color', 'russian_size', 'country',
                'lining_material', 'fastener_type', 'sleeve', 'set_composition',
                'care_instructions'
            ),
            'classes': ('collapse',)
        }),
        ('Даты', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 50px;"/>', obj.image.url)
        return 'Нет фото'

    image_preview.short_description = 'Фото'


@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    form = ProductImageForm
    list_display = ('product', 'image_preview', 'is_main', 'order')
    list_filter = ('is_main', 'product')
    list_editable = ('is_main', 'order')
    fields = ('product', 'image', 'local_path', 'is_main', 'order')

    def image_preview(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="max-height: 100px;"/>', obj.image.url)
        return 'Нет фото'

    image_preview.short_description = 'Превью'


@admin.register(ProductVideo)
class ProductVideoAdmin(admin.ModelAdmin):
    list_display = ('product', 'title', 'is_main', 'order', 'created')
    list_filter = ('is_main', 'product')
    list_editable = ('is_main', 'order')
    search_fields = ('title', 'product__name')


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ('user', 'product', 'added')
    list_filter = ('added',)
    search_fields = ('user__email', 'product__name')