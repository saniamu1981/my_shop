from django.contrib import admin
from django.utils.html import format_html
from .models import Category, Product, ProductImage, ProductVideo, Favorite, ProductSize


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image', 'is_main', 'order', 'preview')
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


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
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
            'fields': ('image',)
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
    list_display = ('product', 'image_preview', 'is_main', 'order')
    list_filter = ('is_main', 'product')
    list_editable = ('is_main', 'order')

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