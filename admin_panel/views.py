from django.contrib.auth import get_user_model
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404
from django.contrib.admin.views.decorators import staff_member_required
from django.views.decorators.http import require_POST

from apps.accounts.models import ChatMessage
from apps.products.models import Product
from apps.orders.models import Order

User = get_user_model()

@staff_member_required
def dashboard(request):
    total_products = Product.objects.count()
    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status='created').count()
    
    context = {
        'total_products': total_products,
        'total_orders': total_orders,
        'pending_orders': pending_orders,
    }
    return render(request, 'admin_panel/dashboard.html', context)


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
