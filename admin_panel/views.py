from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import ChatMessage, Offer
from apps.products.models import Product, Category, Favorite, Review
from apps.orders.models import Order, Cart, Return
from apps.products.models import SiteView, Product, ProductSize
from apps.shop_settings.models import UnitEconomics

User = get_user_model()


@staff_member_required
def dashboard(request):
    """Панель администратора с подробной статистикой."""
    now = timezone.now()
    three_days_ago = now - timedelta(days=3)

    # ===== ТОВАРЫ =====
    total_products = Product.objects.count()

    # Категории с количеством товаров
    categories_stats = (
        Category.objects
        .annotate(products_count=Count('products'))
        .order_by('-products_count')
    )

    # ===== ЗАКАЗЫ =====
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='created').count()

    # Статусы заказов с количеством
    # Иконки и цвета для статусов заказов
    STATUS_ICONS = {
        'created': '🆕',
        'paid': '💰',
        'confirmed': '✅',
        'shipped': '🚚',
        'delivered': '📦',
        'cancelled': '❌',
    }

    status_stats = []
    for code, name in Order.STATUS_CHOICES:
        count = Order.objects.filter(status=code).count()
        status_stats.append({
            'code': code,
            'name': name,
            'count': count,
            'icon': STATUS_ICONS.get(code, '•'),
        })

    # ===== ВОЗВРАТЫ =====
    total_returns = Return.objects.count()

    # Статусы возвратов с количеством
    returns_status_stats = []
    for code, name in Return.STATUS_CHOICES:
        count = Return.objects.filter(status=code).count()
        returns_status_stats.append({
            'code': code,
            'name': name,
            'count': count,
        })

    # ===== ПОЛЬЗОВАТЕЛИ =====
    total_users = User.objects.count()
    superusers_count = User.objects.filter(is_superuser=True).count()
    regular_users_count = total_users - superusers_count
    new_users_3days = User.objects.filter(date_joined__gte=three_days_ago).count()

    # Оферта: принята / не принята
    active_offer = Offer.objects.filter(is_active=True).first()
    offer_accepted = 0
    offer_not_accepted = 0
    if active_offer:
        offer_accepted = User.objects.filter(offer_accepted=active_offer).count()
        offer_not_accepted = total_users - offer_accepted
    else:
        offer_not_accepted = total_users

    # ===== СТАТИСТИКА ТОВАРОВ =====
    # В избранном — сколько раз товары добавили
    favorites_total = Favorite.objects.count()

    # Товары в корзинах (CartItem)
    from apps.orders.models import CartItem
    cart_items_total = CartItem.objects.count()
    cart_unique_products = CartItem.objects.values('product').distinct().count()

    # Топ-5 товаров по добавлениям в избранное
    top_favorites = (
        Product.objects
        .annotate(fav_count=Count('favorited_by'))
        .filter(fav_count__gt=0)
        .order_by('-fav_count')[:5]
    )

    # Топ-5 товаров в корзинах
    top_cart = (
        Product.objects
        .annotate(cart_count=Count('cartitem'))
        .filter(cart_count__gt=0)
        .order_by('-cart_count')[:5]
    )

    # Топ-5 товаров по просмотрам
    top_views = (
        Product.objects
        .filter(views_count__gt=0)
        .order_by('-views_count')[:5]
    )

    # Общее количество просмотров
    total_views = Product.objects.aggregate(total=Sum('views_count'))['total'] or 0

    # Просмотры авторизованными
    total_views_auth = Product.objects.aggregate(total=Sum('views_count_auth'))['total'] or 0

    # Топ-10 городов по просмотрам
    top_cities = (
        SiteView.objects
        .exclude(city='')
        .values('city')
        .annotate(views=Count('id'))
        .order_by('-views')[:10]
    )

    total_site_views = SiteView.objects.count()

    # Топ-10 регионов
    top_regions = (
        SiteView.objects
        .exclude(region='')
        .values('region')
        .annotate(views=Count('id'))
        .order_by('-views')[:10]
    )

    # Топ-5 товаров по заказам (сколько раз товар заказывали)
    top_orders = (
        Product.objects
        .annotate(order_count=Count('orderitem'))
        .filter(order_count__gt=0)
        .order_by('-order_count')[:5]
    )

    # Общее количество позиций в заказах
    from apps.orders.models import OrderItem
    total_order_items = OrderItem.objects.count()

    # ===== РЕЙТИНГИ =====
    # Рейтинг каждого товара (по одобренным отзывам)
    products_ratings = []
    for product in Product.objects.all().order_by('name'):
        reviews = product.reviews.filter(is_approved=True)
        count = reviews.count()
        if count > 0:
            avg = reviews.aggregate(Avg('rating'))['rating__avg'] or 0
        else:
            avg = None
        products_ratings.append({
            'name': product.name,
            'avg_rating': avg,
            'reviews_count': count,
        })

    # Общий рейтинг магазина (средний по всем одобренным отзывам)
    all_reviews = Review.objects.filter(is_approved=True)
    total_reviews_count = all_reviews.count()
    if total_reviews_count > 0:
        shop_avg_rating = all_reviews.aggregate(Avg('rating'))['rating__avg'] or 0
    else:
        shop_avg_rating = None

    unit = UnitEconomics.get_solo()

    unit_formulas = []
    unit_totals = []

    for f in unit.formulas.filter(is_active=True).order_by('order', 'pk'):
        result, error = f.calculate()
        item = {
            'name': f.name,
            'description': f.description,
            'result': result,
            'error': error,
            'is_total': f.is_total,
        }
        if f.is_total:
            unit_totals.append(item)
        else:
            unit_formulas.append(item)

    context = {
        # Товары
        'total_products': total_products,
        'categories_stats': categories_stats,

        # Заказы
        'total_orders': total_orders,
        'pending_orders': pending_orders,
        'status_stats': status_stats,

        # Возвраты
        'returns_status_stats': returns_status_stats,
        'total_returns': total_returns,

        # Пользователи
        'total_users': total_users,
        'superusers_count': superusers_count,
        'regular_users_count': regular_users_count,
        'new_users_3days': new_users_3days,
        'offer_accepted': offer_accepted,
        'offer_not_accepted': offer_not_accepted,
        'active_offer': active_offer,

        # Статистика товаров
        'favorites_total': favorites_total,
        'cart_items_total': cart_items_total,
        'cart_unique_products': cart_unique_products,
        'top_favorites': top_favorites,
        'top_cart': top_cart,
        'top_orders': top_orders,
        'total_order_items': total_order_items,

        # Просмотры/посетители
        'top_views': top_views,
        'total_views': total_views,
        'total_views_auth': total_views_auth,
        'top_cities': top_cities,
        'top_regions': top_regions,
        'total_site_views': total_site_views,

        # Рейтинги
        'products_ratings': products_ratings,
        'shop_avg_rating': shop_avg_rating,
        'total_reviews_count': total_reviews_count,

        # Юнит-экономика
        'unit_formulas': unit_formulas,
        'unit_totals': unit_totals,
    }
    return render(request, 'admin_panel/dashboard.html', context)


@staff_member_required
@require_POST
def reset_views_counters(request):
    """Сбрасывает счётчики просмотров у всех товаров."""
    from apps.products.models import Product

    updated = Product.objects.all().update(views_count=0, views_count_auth=0)

    return JsonResponse({
        'success': True,
        'updated': updated,
    })


@staff_member_required
def chat_list(request):
    """Список пользователей с чатами: сначала непрочитанные, потом прочитанные."""
    from django.db.models import Max, Q

    User = get_user_model()

    # Все пользователи, у которых есть хоть одно сообщение
    users = (
        User.objects
        .filter(chat_messages__isnull=False)
        .distinct()
        .annotate(
            last_message_at=Max('chat_messages__created'),
        )
    )

    # Готовим каждого пользователя: последнее сообщение + количество непрочитанных
    users = list(users)
    for u in users:
        u.last_message = (
            u.chat_messages.order_by('-created').first()
        )
        u.unread_count = u.chat_messages.filter(sender='user', is_read=False).count()

    # Сортируем: сначала непрочитанные (по новизне), потом прочитанные (по новизне)
    users.sort(
        key=lambda u: (
            0 if u.unread_count > 0 else 1,     # сначала непрочитанные
            -(u.last_message_at.timestamp() if u.last_message_at else 0),  # по убыванию даты
        )
    )

    return render(request, 'admin_panel/chat_list.html', {'users': users})


@staff_member_required
def chat_detail(request, user_id):
    """Чат с конкретным пользователем."""
    target_user = get_object_or_404(User, id=user_id)
    messages_qs = ChatMessage.objects.filter(user=target_user).order_by('created')

    # Помечаем сообщения пользователя как прочитанные
    messages_qs.filter(sender='user', is_read=False).update(is_read=True)

    return render(request, 'admin_panel/chat_detail.html', {
        'target_user': target_user,
        'chat_messages': messages_qs,
    })


@staff_member_required
@require_POST
def chat_admin_send(request, user_id):
    """Отправка сообщения от админа пользователю."""
    target_user = get_object_or_404(User, id=user_id)
    text = (request.POST.get('message') or '').strip()
    if not text:
        return JsonResponse({'success': False, 'error': 'Пустое сообщение'}, status=400)

    msg = ChatMessage.objects.create(
        user=target_user,
        sender='admin',
        message=text,
    )

    return JsonResponse({
        'success': True,
        'message': {
            'id': msg.id,
            'sender': msg.sender,
            'message': msg.message,
            'created': msg.created.strftime('%d.%m.%Y %H:%M'),
            'is_read': msg.is_read,
        }
    })


@staff_member_required
def chat_admin_messages(request, user_id):
    """AJAX-получение новых сообщений в чате с пользователем."""
    after_id = request.GET.get('after_id') or 0
    try:
        after_id = int(after_id)
    except (TypeError, ValueError):
        after_id = 0

    qs = ChatMessage.objects.filter(user_id=user_id, id__gt=after_id).order_by('created')
    qs.filter(sender='user', is_read=False).update(is_read=True)

    data = [{
        'id': m.id,
        'sender': m.sender,
        'message': m.message,
        'created': m.created.strftime('%d.%m.%Y %H:%M'),
        'is_read': m.is_read,
    } for m in qs]

    return JsonResponse({'messages': data})


@staff_member_required
@require_POST
def reset_site_views(request):
    """Удаляет все записи просмотров сайта."""
    from apps.products.models import SiteView

    deleted = SiteView.objects.all().delete()

    return JsonResponse({
        'success': True,
        'deleted': deleted[0],  # количество удалённых записей
    })


@staff_member_required
def stock_list(request):
    """Страница управления остатками всех товаров."""
    products = Product.objects.prefetch_related('sizes').order_by('category__name', 'name')
    categories = {}

    for product in products:
        # Готовим цену для каждого размера
        for size in product.sizes.all():
            # Если у размера своя цена — берём её, иначе цену товара
            price = size.price if size.price is not None else product.price
            # Приводим к строке с точкой
            size.display_price = f'{price:.2f}'

        cat_name = product.category.name
        if cat_name not in categories:
            categories[cat_name] = []
        categories[cat_name].append(product)

    return render(request, 'admin_panel/stock_list.html', {
        'categories': categories,
    })


@staff_member_required
@require_POST
def stock_update(request):
    """AJAX-обновление остатков одного размера."""
    size_id = request.POST.get('size_id')
    quantity = request.POST.get('quantity')

    try:
        quantity = int(quantity)
        if quantity < 0:
            quantity = 0
    except (TypeError, ValueError):
        return JsonResponse({'success': False, 'error': 'Некорректное количество'}, status=400)

    try:
        ps = ProductSize.objects.get(id=size_id)
        ps.quantity = quantity
        ps.save(update_fields=['quantity'])

        return JsonResponse({
            'success': True,
            'size_id': ps.id,
            'quantity': ps.quantity,
        })
    except ProductSize.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Размер не найден'}, status=404)


@staff_member_required
@require_POST
def stock_update_price(request):
    """AJAX-обновление цены одного размера."""
    size_id = request.POST.get('size_id')
    price = request.POST.get('price')

    try:
        from decimal import Decimal, InvalidOperation
        price = Decimal(price)
        if price < 0:
            price = Decimal('0')
    except (TypeError, ValueError, InvalidOperation):
        return JsonResponse({'success': False, 'error': 'Некорректная цена'}, status=400)

    try:
        ps = ProductSize.objects.get(id=size_id)
        ps.price = price
        ps.save(update_fields=['price'])

        return JsonResponse({
            'success': True,
            'size_id': ps.id,
            'price': str(ps.price),
        })
    except ProductSize.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Размер не найден'}, status=404)


