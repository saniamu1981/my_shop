from django.http import JsonResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash, logout
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone
from django.views.decorators.http import require_POST

from apps.accounts.models import Offer, ChatMessage
from apps.orders.models import Order
from apps.products.models import Review
import json


@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user).order_by('-created')

    chat_unread_count = 0
    admin_unread_count = 0

    if request.user.is_staff or request.user.is_superuser:
        # Для staff — сколько непрочитанных сообщений от всех пользователей
        admin_unread_count = ChatMessage.objects.filter(sender='user', is_read=False).count()
    else:
        # Для обычного пользователя — сколько непрочитанных ответов админа
        chat_unread_count = ChatMessage.objects.filter(
            user=request.user, sender='admin', is_read=False
        ).count()

    for order in orders:
        order_product_ids = set(order.items.values_list('product_id', flat=True))

        reviewed_ids_in_order = set(
            Review.objects.filter(
                user=request.user,
                order=order,
                product_id__in=order_product_ids
            ).values_list('product_id', flat=True)
        )

        order.has_unreviewed_items = bool(order_product_ids - reviewed_ids_in_order)

    active_offer = Offer.objects.filter(is_active=True).first()
    offer_accepted = bool(
        active_offer and request.user.offer_accepted_id == active_offer.id
    )

    chat_unread_count = ChatMessage.objects.filter(
        user=request.user, sender='admin', is_read=False
    ).count()

    return render(request, 'accounts/profile.html', {
        'orders': orders,
        'user': request.user,
        'active_offer': active_offer,
        'offer_accepted': offer_accepted,
        'admin_unread_count': admin_unread_count,
    })

@login_required
def offer_detail(request, offer_id):
    """Страница просмотра текста оферты + кнопка «Принять»."""
    offer = get_object_or_404(Offer, id=offer_id)

    if request.method == 'POST':
        # Пользователь нажал «Принять»
        request.user.offer_accepted = offer
        request.user.offer_accepted_at = timezone.now()
        request.user.save(update_fields=['offer_accepted', 'offer_accepted_at'])
        messages.success(request, 'Оферта успешно принята')
        return redirect('accounts:profile')

    return render(request, 'accounts/offer_detail.html', {
        'offer': offer,
        'already_accepted': request.user.offer_accepted_id == offer.id,
    })


@login_required
@require_POST
def give_personal_data_consent(request):
    """Пользователь даёт согласие на обработку персональных данных."""
    user = request.user

    if not user.personal_data_consent:
        user.personal_data_consent = True
        user.personal_data_consent_at = timezone.now()
        user.save(update_fields=['personal_data_consent', 'personal_data_consent_at'])
        messages.success(request, 'Согласие на обработку персональных данных получено.')
    else:
        messages.info(request, 'Согласие уже было дано ранее.')

    return redirect('accounts:profile')


@login_required
@require_POST
def revoke_personal_data_consent(request):
    """Пользователь отзывает согласие на обработку персональных данных."""
    user = request.user

    if user.personal_data_consent:
        user.personal_data_consent = False
        user.personal_data_consent_revoked_at = timezone.now()
        user.save(update_fields=[
            'personal_data_consent',
            'personal_data_consent_revoked_at',
        ])
        messages.warning(
            request,
            'Согласие на обработку персональных данных отозвано. '
            'Мы прекратим обработку данных, кроме тех, что нужны для исполнения '
            'заказа и требований законодательства.'
        )
    else:
        messages.info(request, 'Согласие уже было отозвано ранее.')

    return redirect('accounts:profile')


@login_required
def edit_profile(request):
    if request.method == 'POST':
        user = request.user
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.phone = request.POST.get('phone', user.phone)
        user.save()
        messages.success(request, 'Профиль успешно обновлен')
        return redirect('accounts:profile')

    return render(request, 'accounts/edit_profile.html', {'user': request.user})


@login_required
def change_password(request):
    if request.method == 'POST':
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, 'Пароль успешно изменен')
            return redirect('accounts:profile')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки')
    else:
        form = PasswordChangeForm(request.user)

    return render(request, 'accounts/change_password.html', {'form': form})


@login_required
def chat(request):
    # Staff и суперюзеры видят чат со стороны админки, а не со стороны пользователя
    if request.user.is_staff or request.user.is_superuser:
        return redirect('admin_panel:chat_list')

    """Страница чата пользователя с суперадмином."""
    messages_qs = ChatMessage.objects.filter(user=request.user).order_by('created')

    # Отмечаем ответы админа как прочитанные пользователем
    messages_qs.filter(sender='admin', is_read=False).update(is_read=True)

    return render(request, 'accounts/chat.html', {
        'chat_messages': messages_qs,
    })


@login_required
@require_POST
def chat_send(request):
    """Отправка сообщения пользователем."""
    text = (request.POST.get('message') or '').strip()
    if not text:
        return JsonResponse({'success': False, 'error': 'Пустое сообщение'}, status=400)

    msg = ChatMessage.objects.create(
        user=request.user,
        sender='user',
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


@login_required
def chat_messages(request):
    """AJAX-получение новых сообщений (для автообновления)."""
    after_id = request.GET.get('after_id') or 0
    try:
        after_id = int(after_id)
    except (TypeError, ValueError):
        after_id = 0

    qs = ChatMessage.objects.filter(
        user=request.user, id__gt=after_id
    ).order_by('created')

    # Отмечаем ответы админа как прочитанные
    qs.filter(sender='admin', is_read=False).update(is_read=True)

    data = [{
        'id': m.id,
        'sender': m.sender,
        'message': m.message,
        'created': m.created.strftime('%d.%m.%Y %H:%M'),
        'is_read': m.is_read,
    } for m in qs]

    return JsonResponse({'messages': data})


@login_required
@require_POST
def profile_delete(request):
    user = request.user

    # Защита: суперпользователь не может удалить свой профиль
    if user.is_superuser:
        messages.error(request, 'Суперпользователь не может удалить свой профиль.')
        return redirect('accounts:profile')

    # Сохраняем email для сообщения
    email = user.email

    # Разлогиниваем и удаляем пользователя
    logout(request)
    user.delete()

    messages.success(
        request,
        f'Профиль {email} был удалён. Спасибо, что были с нами.'
    )
    return redirect('home')


@login_required
@require_POST
def toggle_webpush(request):
    """Переключение пуш-уведомлений пользователя (AJAX)."""
    try:
        data = json.loads(request.body or '{}')
    except (ValueError, TypeError):
        data = {}

    enabled = bool(data.get('enabled', True))

    user = request.user
    user.webpush_enabled = enabled
    user.save(update_fields=['webpush_enabled'])

    return JsonResponse({
        'success': True,
        'webpush_enabled': user.webpush_enabled,
    })