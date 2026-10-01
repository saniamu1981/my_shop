from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST
from django.db.models import Count, Q, Sum
from django.utils import timezone
from datetime import timedelta

from apps.accounts.models import ChatMessage, Offer
from apps.products.models import Product, Category, Favorite
from apps.orders.models import Order, Cart, Return

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
    status_stats = []
    for code, name in Order.STATUS_CHOICES:
        count = Order.objects.filter(status=code).count()
        status_stats.append({
            'code': code,
            'name': name,
            'count': count,
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

        # Просмотры/посетители
        'top_views': top_views,
        'total_views': total_views,
        'total_views_auth': total_views_auth,
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
