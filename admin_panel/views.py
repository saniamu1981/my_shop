import json

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, Sum, Avg
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import ChatMessage, Offer
from apps.products.models import Product, Category, Favorite, Review, SiteView, ProductSize
from apps.orders.models import Order, Cart, Return
from apps.shop_settings.models import UnitEconomics, ExcludedCity, UnitVariable, UnitFormula, ProductCost
from django.core.paginator import Paginator

import csv
from django.http import HttpResponse

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
    excluded_cities = list(
        ExcludedCity.objects.values_list('city', flat=True)
    )

    top_cities = (
        SiteView.objects
        .exclude(city='')
        .exclude(city__in=excluded_cities)
        .values('city')
        .annotate(views=Count('id'))
        .order_by('-views')[:10]
    )

    total_site_views = (
        SiteView.objects
        .exclude(city='')
        .exclude(city__in=excluded_cities)
        .count()
    )

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
    products_qs = Product.objects.annotate(
        approved_count=Count('reviews', filter=Q(reviews__is_approved=True)),
        pending_count=Count(
            'reviews',
            filter=Q(reviews__is_approved=False, reviews__is_rejected=False),
        ),
        avg_rating=Avg('reviews__rating', filter=Q(reviews__is_approved=True)),
    ).order_by('name')

    for p in products_qs:
        products_ratings.append({
            'name': p.name,
            'avg_rating': p.avg_rating,
            'reviews_count': p.approved_count,
            'pending_count': p.pending_count,
        })

    # Общий рейтинг магазина (средний по всем одобренным отзывам)
    all_reviews = Review.objects.filter(is_approved=True)
    total_reviews_count = all_reviews.count()
    total_pending_reviews = Review.objects.filter(
        is_approved=False,
        is_rejected=False,
    ).count()
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
        'total_pending_reviews': total_pending_reviews,

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


@staff_member_required
@require_POST
def delete_city_views(request):
    """Удаляет все SiteView указанного города (без чёрного списка)."""
    city = (request.POST.get('city') or '').strip()

    if not city:
        return JsonResponse({'success': False, 'error': 'Город не указан'}, status=400)

    deleted, _ = SiteView.objects.filter(city=city).delete()

    return JsonResponse({
        'success': True,
        'deleted': deleted,
        'city': city,
    })


@staff_member_required
@require_POST
def exclude_city(request):
    """Добавляет город в чёрный список и удаляет его SiteView."""
    city = (request.POST.get('city') or '').strip()

    if not city:
        return JsonResponse({'success': False, 'error': 'Город не указан'}, status=400)

    ExcludedCity.objects.get_or_create(city=city)
    deleted, _ = SiteView.objects.filter(city=city).delete()

    return JsonResponse({
        'success': True,
        'deleted': deleted,
        'city': city,
        'excluded': True,
    })


@staff_member_required
def review_moderation(request):
    """Страница модерации отзывов.

    Два блока:
    - «На модерации» — ожидают решения (is_approved=False, is_rejected=False)
    - «Одобренные и отклонённые» — уже обработаны (is_approved=True или is_rejected=True)
    """
    from apps.products.models import Review

    # ===== Блок 1: на модерации =====
    pending_qs = (
        Review.objects
        .filter(is_approved=False, is_rejected=False)
        .select_related('product', 'user', 'order')
        .order_by('-created')
    )

    pending_paginator = Paginator(pending_qs, 20)
    pending_page = request.GET.get('pending_page', 1)
    try:
        pending_reviews = pending_paginator.page(pending_page)
    except Exception:
        pending_reviews = pending_paginator.page(1)

    for r in pending_reviews:
        r.media_list = list(r.media.all().order_by('order'))

    # ===== Блок 2: одобренные и отклонённые =====
    processed_qs = (
        Review.objects
        .filter(Q(is_approved=True) | Q(is_rejected=True))
        .select_related('product', 'user', 'order')
        .order_by('-updated', '-created')
    )

    # Фильтр по статусу (все / одобренные / отклонённые)
    status_filter = request.GET.get('status', 'all')
    if status_filter == 'approved':
        processed_qs = processed_qs.filter(is_approved=True, is_rejected=False)
    elif status_filter == 'rejected':
        processed_qs = processed_qs.filter(is_rejected=True)

    processed_paginator = Paginator(processed_qs, 20)
    processed_page = request.GET.get('processed_page', 1)
    try:
        processed_reviews = processed_paginator.page(processed_page)
    except Exception:
        processed_reviews = processed_paginator.page(1)

    for r in processed_reviews:
        r.media_list = list(r.media.all().order_by('order'))

    return render(request, 'admin_panel/review_moderation.html', {
        'pending_reviews': pending_reviews,
        'total_pending': pending_qs.count(),
        'processed_reviews': processed_reviews,
        'total_processed': processed_qs.count(),
        'status_filter': status_filter,
    })


@staff_member_required
@require_POST
def review_approve(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.is_approved = True
    review.is_rejected = False
    review.save(update_fields=['is_approved', 'is_rejected'])
    return JsonResponse({
        'success': True,
        'review_id': review.id,
        'action': 'approved',
    })


@staff_member_required
@require_POST
def review_reject(request, review_id):
    review = get_object_or_404(Review, id=review_id)
    review.is_approved = False
    review.is_rejected = True
    review.save(update_fields=['is_approved', 'is_rejected'])
    return JsonResponse({
        'success': True,
        'review_id': review.id,
        'action': 'rejected',
    })



@staff_member_required
def unit_economics_page(request):
    """Кастомная страница юнит-экономики."""
    unit = UnitEconomics.get_solo()

    # Переменные
    variables = list(unit.variables.all().order_by('name'))

    # Товары с себестоимостью (создаём ProductCost при отсутствии)
    products = Product.objects.all().order_by('category__name', 'name')
    existing_costs = {
        pc.product_id: pc
        for pc in ProductCost.objects.filter(unit=unit)
    }
    product_costs = []
    for p in products:
        pc = existing_costs.get(p.id)
        if pc is None:
            pc = ProductCost.objects.create(unit=unit, product=p, cost=0)
        product_costs.append({
            'product': p,
            'cost': pc.cost,
            'id': pc.id,
        })

    # Формулы
    formulas = []
    for f in unit.formulas.filter(is_active=True).order_by('order', 'pk'):
        result, error = f.calculate()
        formulas.append({
            'obj': f,
            'name': f.name,
            'description': f.description,
            'expression': f.expression or [],
            'expression_json': json.dumps(f.expression or []),  # ← добавить
            'order': f.order,
            'is_total': f.is_total,
            'is_active': f.is_active,
            'result': result,
            'error': error,
        })

    # Встроенные метрики — из реестра
    from apps.shop_settings.models import BUILTIN_METRICS
    builtin_metrics = [
        {'code': code, 'label': meta['label']}
        for code, meta in BUILTIN_METRICS.items()
    ]

    print('=== UNIT PAGE DEBUG ===')
    print('variables:', [(v.id, v.name, v.value) for v in variables])
    print('formulas:', [(f['name'], f['order']) for f in formulas])
    print('product_costs:', [(pc['product'].name, pc['cost']) for pc in product_costs])
    print('builtin count:', len(builtin_metrics))

    return render(request, 'admin_panel/unit_economics.html', {
        'unit': unit,
        'variables': variables,
        'product_costs': product_costs,
        'formulas': formulas,
        'builtin_metrics': builtin_metrics,
    })


@staff_member_required
@require_POST
def unit_variable_save(request):
    """Создать или обновить переменную."""
    variable_id = request.POST.get('id')
    name = (request.POST.get('name') or '').strip()
    value = request.POST.get('value') or '0'
    description = (request.POST.get('description') or '').strip()

    if not name:
        return JsonResponse({'success': False, 'error': 'Укажите название'}, status=400)

    try:
        from decimal import Decimal, InvalidOperation
        value = Decimal(value)
    except (InvalidOperation, TypeError):
        return JsonResponse({'success': False, 'error': 'Некорректное значение'}, status=400)

    unit = UnitEconomics.get_solo()

    if variable_id:
        var = get_object_or_404(UnitVariable, id=variable_id, unit=unit)
    else:
        var = UnitVariable(unit=unit)

    var.name = name
    var.value = value
    var.description = description
    var.save()

    return JsonResponse({
        'success': True,
        'variable': {
            'id': var.id,
            'name': var.name,
            'value': str(var.value),
            'description': var.description,
        },
    })


@staff_member_required
@require_POST
def unit_variable_delete(request):
    """Удалить переменную."""
    variable_id = request.POST.get('id')
    if not variable_id:
        return JsonResponse({'success': False, 'error': 'Не указан id'}, status=400)

    UnitVariable.objects.filter(id=variable_id).delete()
    return JsonResponse({'success': True})


@staff_member_required
@require_POST
def unit_cost_save(request):
    """Обновить себестоимость товара."""
    pc_id = request.POST.get('id')
    cost = request.POST.get('cost') or '0'

    if not pc_id:
        return JsonResponse({'success': False, 'error': 'Не указан id'}, status=400)

    try:
        from decimal import Decimal, InvalidOperation
        cost = Decimal(cost)
    except (InvalidOperation, TypeError):
        return JsonResponse({'success': False, 'error': 'Некорректная цена'}, status=400)

    pc = get_object_or_404(ProductCost, id=pc_id)
    pc.cost = cost
    pc.save(update_fields=['cost'])

    return JsonResponse({
        'success': True,
        'cost': str(pc.cost),
    })


@staff_member_required
@require_POST
def unit_formula_save(request):
    """Создать или обновить формулу."""
    try:
        data = json.loads(request.body)
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Bad JSON'}, status=400)

    formula_id = data.get('id')
    name = (data.get('name') or '').strip()
    description = (data.get('description') or '').strip()
    expression = data.get('expression') or []
    order = data.get('order', 0)
    is_total = bool(data.get('is_total', False))
    is_active = bool(data.get('is_active', True))

    if not name:
        return JsonResponse({'success': False, 'error': 'Укажите название'}, status=400)
    if not expression:
        return JsonResponse({'success': False, 'error': 'Формула пуста'}, status=400)

    unit = UnitEconomics.get_solo()

    if formula_id:
        formula = get_object_or_404(UnitFormula, id=formula_id, unit=unit)
    else:
        formula = UnitFormula(unit=unit)

    formula.name = name
    formula.description = description
    formula.expression = expression
    formula.order = order
    formula.is_total = is_total
    formula.is_active = is_active
    formula.save()

    result, error = formula.calculate()

    return JsonResponse({
        'success': True,
        'formula': {
            'id': formula.id,
            'name': formula.name,
            'description': formula.description,
            'expression': formula.expression,
            'order': formula.order,
            'is_total': formula.is_total,
            'is_active': formula.is_active,
            'result': str(result) if result is not None else None,
            'error': error,
        },
    })


@staff_member_required
@require_POST
def unit_formula_delete(request):
    """Удалить формулу."""
    formula_id = request.POST.get('id')
    if not formula_id:
        return JsonResponse({'success': False, 'error': 'Не указан id'}, status=400)

    UnitFormula.objects.filter(id=formula_id).delete()
    return JsonResponse({'success': True})




@staff_member_required
def users_list(request):
    """Кастомная страница пользователей."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    qs = User.objects.all().order_by('-date_joined')

    # ===== Поиск =====
    search_query = (request.GET.get('q') or '').strip()
    if search_query:
        qs = qs.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(phone__icontains=search_query)
        )

    # ===== Фильтры =====
    is_staff = request.GET.get('is_staff')
    if is_staff == 'yes':
        qs = qs.filter(is_staff=True)
    elif is_staff == 'no':
        qs = qs.filter(is_staff=False)

    is_superuser = request.GET.get('is_superuser')
    if is_superuser == 'yes':
        qs = qs.filter(is_superuser=True)
    elif is_superuser == 'no':
        qs = qs.filter(is_superuser=False)

    is_active = request.GET.get('is_active')
    if is_active == 'yes':
        qs = qs.filter(is_active=True)
    elif is_active == 'no':
        qs = qs.filter(is_active=False)

    consent = request.GET.get('consent')
    if consent == 'yes':
        qs = qs.filter(personal_data_consent=True)
    elif consent == 'no':
        qs = qs.filter(personal_data_consent=False)

    # ===== Сортировка =====
    sort = request.GET.get('sort', '-date_joined')
    allowed_sorts = {
        'email': 'email',
        '-email': '-email',
        'first_name': 'first_name',
        '-first_name': '-first_name',
        'last_name': 'last_name',
        '-last_name': '-last_name',
        'date_joined': 'date_joined',
        '-date_joined': '-date_joined',
        'is_staff': 'is_staff',
        '-is_staff': '-is_staff',
    }
    qs = qs.order_by(allowed_sorts.get(sort, '-date_joined'))

    # ===== Пагинация =====
    from django.core.paginator import Paginator
    paginator = Paginator(qs, 25)
    page = request.GET.get('page', 1)
    try:
        users = paginator.page(page)
    except Exception:
        users = paginator.page(1)

    # ===== Оферта =====
    from apps.accounts.models import Offer
    active_offer = Offer.objects.filter(is_active=True).first()

    for u in users:
        u.offer_accepted_flag = bool(
            active_offer and u.offer_accepted_id == active_offer.id
        )

    context = {
        'users': users,
        'total_users': qs.count(),
        'search_query': search_query,
        'is_staff_filter': is_staff or '',
        'is_superuser_filter': is_superuser or '',
        'is_active_filter': is_active or '',
        'consent_filter': consent or '',
        'sort': sort,
        'active_offer': active_offer,
    }
    return render(request, 'admin_panel/users_list.html', context)


@staff_member_required
def user_detail(request, user_id):
    """Страница редактирования пользователя."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user_obj = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        user_obj.email = request.POST.get('email', user_obj.email)
        user_obj.first_name = request.POST.get('first_name', '')
        user_obj.last_name = request.POST.get('last_name', '')
        user_obj.phone = request.POST.get('phone', '')
        user_obj.is_active = request.POST.get('is_active') == 'on'
        user_obj.is_staff = request.POST.get('is_staff') == 'on'
        user_obj.is_superuser = request.POST.get('is_superuser') == 'on'
        user_obj.personal_data_consent = request.POST.get('personal_data_consent') == 'on'

        # Проверка: суперпользователь не может снять с себя is_superuser
        if request.user.id == user_obj.id and not user_obj.is_superuser:
            user_obj.is_superuser = True

        user_obj.save()

        messages.success(request, f'Пользователь {user_obj.email} сохранён')
        return redirect('admin_panel:user_detail', user_id=user_obj.id)

    # Считаем статистику
    from apps.orders.models import Order
    from apps.products.models import Review

    context = {
        'user_obj': user_obj,
        'orders_count': Order.objects.filter(user=user_obj).count(),
        'reviews_count': Review.objects.filter(user=user_obj).count(),
    }
    return render(request, 'admin_panel/user_detail.html', context)


@staff_member_required
@require_POST
def user_delete(request, user_id):
    """AJAX-удаление пользователя."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    user_obj = get_object_or_404(User, id=user_id)

    if user_obj.is_superuser:
        return JsonResponse({
            'success': False,
            'error': 'Нельзя удалить суперпользователя',
        }, status=403)

    email = user_obj.email
    user_obj.delete()
    return JsonResponse({'success': True, 'email': email})


@staff_member_required
@require_POST
def users_bulk_action(request):
    """Массовые действия над пользователями."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    action = request.POST.get('action')
    ids = request.POST.getlist('ids[]') or request.POST.get('ids', '').split(',')

    try:
        ids = [int(i) for i in ids if str(i).strip()]
    except (ValueError, TypeError):
        return JsonResponse({'success': False, 'error': 'Некорректные IDs'}, status=400)

    if not ids:
        return JsonResponse({'success': False, 'error': 'Не выбрано ни одного пользователя'}, status=400)

    qs = User.objects.filter(id__in=ids)

    if action == 'activate':
        qs.update(is_active=True)
        return JsonResponse({'success': True, 'updated': qs.count(), 'action': 'activate'})

    if action == 'deactivate':
        # Не деактивировать самого себя
        qs = qs.exclude(id=request.user.id)
        qs.update(is_active=False)
        return JsonResponse({'success': True, 'updated': qs.count(), 'action': 'deactivate'})

    if action == 'delete':
        qs = qs.filter(is_superuser=False).exclude(id=request.user.id)
        count = qs.count()
        qs.delete()
        return JsonResponse({'success': True, 'deleted': count, 'action': 'delete'})

    return JsonResponse({'success': False, 'error': 'Неизвестное действие'}, status=400)


@staff_member_required
def users_export(request):
    """Выгрузка пользователей в CSV."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    qs = User.objects.all().order_by('-date_joined')

    response = HttpResponse(content_type='text/csv; charset=utf-8')
    response['Content-Disposition'] = 'attachment; filename="users.csv"'
    response.write('\ufeff')  # BOM для Excel

    writer = csv.writer(response)
    writer.writerow([
        'ID', 'Email', 'Имя', 'Фамилия', 'Телефон',
        'Активен', 'Персонал', 'Суперпользователь',
        'Согласие на ПД', 'Дата регистрации',
    ])

    for u in qs:
        writer.writerow([
            u.id,
            u.email,
            u.first_name,
            u.last_name,
            getattr(u, 'phone', ''),
            'Да' if u.is_active else 'Нет',
            'Да' if u.is_staff else 'Нет',
            'Да' if u.is_superuser else 'Нет',
            'Да' if u.personal_data_consent else 'Нет',
            u.date_joined.strftime('%d.%m.%Y %H:%M'),
        ])

    return response