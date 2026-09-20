# apps/products/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Product, Category

class ProductSitemap(Sitemap):
    changefreq = "daily"  # Как часто меняется страница
    priority = 0.8        # Приоритет страницы (от 0.0 до 1.0)

    def items(self):
        # Возвращаем все товары, которые есть в наличии
        return Product.objects.filter(available=True)

    def lastmod(self, obj):
        # Дата последнего обновления товара
        return obj.updated

    def location(self, obj):
        # URL страницы товара
        return obj.get_absolute_url()

class CategorySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return Category.objects.all()

    def location(self, obj):
        return obj.get_absolute_url()

class StaticViewSitemap(Sitemap):
    """Карта для статичных страниц (главная, оферта и т.д.)"""
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        # Имена URL-маршрутов из вашего urls.py
        return ['home']  # Добавьте сюда другие важные страницы

    def location(self, item):
        return reverse(item)