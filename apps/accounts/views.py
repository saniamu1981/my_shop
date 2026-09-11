from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.utils import timezone

from apps.accounts.models import Offer
from apps.orders.models import Order


@login_required
def profile(request):
    orders = Order.objects.filter(user=request.user).order_by('-created')
    active_offer = Offer.objects.filter(is_active=True).first()

    # Принята ли активная оферта?
    offer_accepted = False
    if active_offer and request.user.offer_accepted_id == active_offer.id:
        offer_accepted = True

    return render(request, 'accounts/profile.html', {
        'orders': orders,
        'user': request.user,
        'active_offer': active_offer,
        'offer_accepted': offer_accepted,
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