from django.http import HttpResponse
from django.utils import timezone
from .models import Product, Category


def yml_feed(request):
    # Получаем все товары и категории
    products = Product.objects.filter(available=True)
    categories = Category.objects.all()

    # Получаем базовый URL сайта (например, http://ваш-сайт.ru)
    site_url = request.build_absolute_uri('/')[:-1]

    # Формируем XML
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<yml_catalog date="{}">\n'.format(timezone.now().strftime('%Y-%m-%d %H:%M'))
    xml += '  <shop>\n'
    xml += '    <name>Maidlingerie</name>\n'
    xml += '    <company>ИП Музырев А.С.</company>\n'
    xml += '    <url>{}</url>\n'.format(site_url)

    # Валюты
    xml += '    <currencies>\n'
    xml += '      <currency id="RUB" rate="1"/>\n'
    xml += '    </currencies>\n'

    # Категории
    xml += '    <categories>\n'
    for cat in categories:
        xml += '      <category id="{}">{}</category>\n'.format(cat.id, cat.name)
    xml += '    </categories>\n'

    # Товары
    xml += '    <offers>\n'
    for product in products:
        # Ссылка на товар (используйте reverse или get_absolute_url)
        product_url = site_url + product.get_absolute_url()

        # Изображение
        image_url = ''
        if product.image:
            img = product.image.url
            if img.startswith('http://') or img.startswith('https://'):
                image_url = img
            else:
                image_url = site_url + img

        # Формируем офер
        xml += '      <offer id="{}" available="true">\n'.format(product.sku)
        xml += '        <url>{}</url>\n'.format(product_url)
        xml += '        <price>{}</price>\n'.format(int(product.price))
        xml += '        <currencyId>RUB</currencyId>\n'
        xml += '        <categoryId>{}</categoryId>\n'.format(product.category.id)
        if image_url:
            xml += '        <picture>{}</picture>\n'.format(image_url)
        xml += '        <name>{}</name>\n'.format(product.name)
        xml += '      </offer>\n'
    xml += '    </offers>\n'
    xml += '  </shop>\n'
    xml += '</yml_catalog>'

    return HttpResponse(xml, content_type='application/xml')