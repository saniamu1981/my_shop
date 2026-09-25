import json
import uuid

from yookassa import Configuration, Payment
from yookassa.domain.exceptions import ApiError

from django.conf import settings
from django.http import JsonResponse, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.views.decorators.csrf import csrf_exempt

from .models import Order, OrderItem
from apps.cart.cart import CartManager
from apps.products.models import Product, Review, ReviewMedia
from django.contrib.auth import get_user_model
from apps.accounts.utils import send_push_safe

from django.views.decorators.http import require_POST
from .forms import ReturnCreateForm
from .models import Return, ReturnItem, ReturnPhoto


# ============ Настройка ЮKassa ============
Configuration.account_id = settings.YOOKASSA_SHOP_ID
Configuration.secret_key = settings.YOOKASSA_SECRET_KEY


# apps/orders/views.py

@login_required
def order_list(request):
    """Список заказов пользователя + заявок на возврат."""
    orders = Order.objects.filter(user=request.user).order_by('-created')

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

        # Есть ли активная заявка на возврат по этому заказу?
        order.has_active_return = order.returns.exclude(status='cancelled').exists()

    # Возвраты пользователя
    returns = Return.objects.filter(user=request.user).select_related('order').order_by('-created')

    paginator = Paginator(orders, 10)
    page = request.GET.get('page')
    orders = paginator.get_page(page)

    # Пагинация для возвратов (отдельная страница)
    returns_paginator = Paginator(returns, 10)
    returns_page = request.GET.get('returns_page')
    returns = returns_paginator.get_page(returns_page)

    return render(request, 'orders/order_list.html', {
        'orders': orders,
        'returns': returns,
    })


@login_required
def create_order(request):
    cart = CartManager(request)
    from_param = request.GET.get('from') or request.POST.get('from', '')

    if from_param == 'cart':
        # Пришли из корзины — игнорируем buy_now
        buy_now_data = None
        if 'buy_now' in request.session:
            request.session.pop('buy_now', None)
            request.session.modified = True
    else:
        # Пришли из buy_now — берём из сессии
        buy_now_data = request.session.get('buy_now')

    # ===== Если в корзине пусто и нет быстрой покупки — уходим =====
    if cart.is_empty() and not buy_now_data:
        messages.warning(request, 'Корзина пуста')
        return redirect('products:product_list')

    # ===== Проверка оферты =====
    from apps.accounts.models import Offer
    active_offer = Offer.objects.filter(is_active=True).first()

    if active_offer and request.user.offer_accepted_id != active_offer.id:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            from django.urls import reverse
            return JsonResponse({
                'success': False,
                'offer_required': True,
                'offer_url': reverse('accounts:offer_detail', args=[active_offer.id]),
                'profile_url': reverse('accounts:profile'),
                'message': 'Для оформления заказа необходимо принять оферту.',
            })
        messages.warning(request, 'Для оформления заказа необходимо принять оферту.')
        return redirect('accounts:profile')

    # ===== Проверка согласия на обработку ПД =====
    if not request.user.personal_data_consent:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            from django.urls import reverse
            return JsonResponse({
                'success': False,
                'consent_required': True,
                'profile_url': reverse('accounts:profile'),
                'message': 'Для оформления заказа необходимо согласие на обработку персональных данных.',
            })
        messages.warning(
            request,
            'Для оформления заказа необходимо согласие на обработку персональных данных. '
            'Дайте согласие в личном кабинете.'
        )
        return redirect('accounts:profile')

    # ===== POST — создаём заказ =====
    if request.method == 'POST':
        delivery_method = request.POST.get('delivery_method', '')
        delivery_point_raw = request.POST.get('delivery_point', '{}')

        point_data = {}
        if delivery_point_raw:
            # 1. Пробуем как JSON (приходит из JS-формы)
            try:
                parsed = json.loads(delivery_point_raw)
                if isinstance(parsed, dict):
                    point_data = parsed
            except Exception:
                pass

            # 2. Если не получилось — пробуем формат "code|name|address"
            if not point_data and '|' in delivery_point_raw:
                parts = delivery_point_raw.split('|', 2)
                if len(parts) == 3:
                    point_data = {
                        'code': parts[0],
                        'name': parts[1],
                        'address': parts[2],
                    }

        # ---- Считаем сумму и собираем позиции ----
        if buy_now_data:
            # быстрая покупка — один товар из сессии
            product = get_object_or_404(Product, id=buy_now_data.get('product_id'))
            quantity = int(buy_now_data.get('quantity', 1) or 1)
            price = product.price
            total_price = price * quantity

            order_items_data = [{
                'product': product,
                'price': price,
                'quantity': quantity,
            }]
        else:
            # обычная корзина
            total_price = cart.get_total_price()
            order_items_data = [{
                'product': item['product'],
                'price': item['price'],
                'quantity': item['quantity'],
            } for item in cart]

        order = Order.objects.create(
            user=request.user,
            first_name=request.POST.get('first_name', ''),
            last_name=request.POST.get('last_name', ''),
            email=request.POST.get('email', ''),
            address=point_data.get('address') or request.POST.get('address', ''),
            phone=request.POST.get('phone', ''),
            total_price=total_price,
            delivery_method=delivery_method,
            delivery_point_code=point_data.get('code', ''),
            delivery_point_name=point_data.get('name', ''),
            delivery_point_address=point_data.get('address', ''),
        )

        for item in order_items_data:
            OrderItem.objects.create(
                order=order,
                product=item['product'],
                price=item['price'],
                quantity=item['quantity'],
            )

        # ===== Уведомление админам о новом заказе =====
        try:
            User = get_user_model()
            admins = User.objects.filter(is_staff=True, is_active=True)
            payload = {
                "head": "🛍 Новый заказ!",
                "body": f"Заказ №{order.id} на сумму {order.total_price} ₽",
                "icon": "/static/icons/icon-192x192.png",
                "url": f"/admin/orders/order/{order.id}/change/",  # куда вести при клике
            }
            for admin in admins:
                send_push_safe(admin, payload)
        except Exception as e:
            print(f'Webpush general error: {e}')

        # ---- Чистим источники ----
        if buy_now_data:
            # Удаляем товар из корзины, если он там был (при buy-now обычно нет)
            size = buy_now_data.get('size') or ''
            try:
                cart.remove(order_items_data[0]['product'].id, size=size)
            except Exception:
                pass
            request.session.pop('buy_now', None)
            request.session.modified = True
        else:
            cart.clear()

        # ---- Ответ ----
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            from django.urls import reverse
            return JsonResponse({
                'success': True,
                'order_id': order.id,
                'redirect_url': reverse('orders:payment_process', args=[order.id]),
            })

        messages.success(request, f'Заказ №{order.id} успешно создан')
        return redirect('orders:payment_process', order_id=order.id)

    # ===== GET — рендерим форму =====
    # Показываем в правой колонке либо корзину, либо один товар быстрой покупки
    if buy_now_data:
        product = get_object_or_404(Product, id=buy_now_data.get('product_id'))
        cart_context = [{
            'product': product,
            'price': product.price,
            'quantity': int(buy_now_data.get('quantity', 1) or 1),
            'total_price': product.price * int(buy_now_data.get('quantity', 1) or 1),
        }]
        total_price = sum(x['total_price'] for x in cart_context)
    else:
        cart_context = list(cart)
        total_price = cart.get_total_price()

    # Достаём данные доставки из URL (если пришли с product_detail)
    dp_address = request.GET.get('dp_address', '')
    dp_method = request.GET.get('delivery_method', '')
    dp_code = request.GET.get('dp_code', '')
    dp_name = request.GET.get('dp_name', '')

    # Если в URL ничего нет — пробуем взять из сессии (buy_now)
    if not dp_address and buy_now_data:
        bp = buy_now_data.get('delivery_point') or {}
        dp_address = bp.get('address', '')
        dp_code = bp.get('code', '')
        dp_name = bp.get('name', '')
        dp_method = buy_now_data.get('delivery_method', '')

    return render(request, 'orders/order_create.html', {
        'cart': cart_context,
        'total_price': total_price,
        'buy_now': bool(buy_now_data),
        'dp_address': dp_address,
        'dp_code': dp_code,
        'dp_name': dp_name,
        'dp_method': dp_method,
    })


@login_required
def payment_process(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.paid:
        messages.info(request, 'Заказ уже оплачен')
        return redirect('orders:order_detail', order_id=order.id)

    if order.status == 'cancelled':
        messages.error(request, 'Этот заказ был отменен')
        return redirect('orders:order_detail', order_id=order.id)

    try:
        # return_url — куда вернётся пользователь после оплаты
        return_url = request.build_absolute_uri(
            reverse('orders:payment_success', args=[order.id])
        )

        # Формируем список позиций для чека
        items_for_receipt = []
        for item in order.items.all():
            items_for_receipt.append({
                "description": item.product.name[:128],
                "quantity": item.quantity,
                "amount": {
                    "value": f"{item.price:.2f}",
                    "currency": "RUB"
                },
                "vat_code": 1,
                "payment_subject": "commodity",  # ← признак предмета расчёта
                "payment_mode": "full_payment",  # ← признак способа расчёта
            })

        payment = Payment.create({
            "amount": {
                "value": f"{order.total_price:.2f}",
                "currency": "RUB",
            },
            "capture": True,
            "confirmation": {
                "type": "redirect",
                "return_url": return_url,
            },
            "description": f"Заказ №{order.id}",
            "receipt": {
                "customer": {"email": order.email},
                "items": items_for_receipt,
            },
            "metadata": {
                "order_id": str(order.id),
            },
        }, uuid.uuid4())

        order.payment_id = payment.id
        order.save()

        # Редиректим пользователя на страницу оплаты ЮKassa
        return redirect(payment.confirmation.confirmation_url)

    except ApiError as e:
        messages.error(request, f'Ошибка оплаты: {e}')
        return redirect('orders:order_detail', order_id=order.id)
    except Exception as e:
        messages.error(request, f'Ошибка оплаты: {e}')
        return redirect('orders:order_detail', order_id=order.id)


@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Проверяем статус оплаты через ЮKassa API
    try:
        if order.payment_id:
            payment = Payment.find_one(order.payment_id)
            if payment.status == 'succeeded' and not order.paid:
                order.paid = True
                order.status = 'paid'
                order.save()
                messages.success(request, f'Заказ №{order.id} успешно оплачен!')
            elif not order.paid:
                messages.info(request, 'Оплата еще обрабатывается. Проверьте статус через минуту.')
        else:
            messages.warning(request, 'Не найден идентификатор платежа.')
    except Exception as e:
        messages.error(request, f'Не удалось проверить статус оплаты: {e}')

    return render(request, 'orders/payment_success.html', {'order': order})


@csrf_exempt
def yookassa_webhook(request):
    """Уведомления от ЮKassa о смене статуса платежа."""
    if request.method != 'POST':
        return HttpResponse(status=405)

    try:
        event_json = json.loads(request.body)
        event = event_json.get('event')
        payment_object = event_json.get('object', {})

        if event == 'payment.succeeded':
            order_id = payment_object.get('metadata', {}).get('order_id')
            payment_id = payment_object.get('id')

            if order_id:
                order = Order.objects.filter(id=order_id).first()
                if order and not order.paid:
                    order.paid = True
                    order.status = 'paid'
                    order.payment_id = payment_id or order.payment_id
                    order.save()

        elif event == 'payment.canceled':
            order_id = payment_object.get('metadata', {}).get('order_id')
            if order_id:
                order = Order.objects.filter(id=order_id).first()
                if order and not order.paid:
                    order.status = 'cancelled'
                    order.save()

        return HttpResponse(status=200)

    except Exception as e:
        print(f'YooKassa webhook error: {e}')
        return HttpResponse(status=500)


@login_required
def payment_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    messages.warning(request, 'Платеж был отменен')
    return render(request, 'orders/payment_cancel.html', {'order': order})


@login_required
def order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/order_detail.html', {'order': order})


@login_required
def cancel_order(request, order_id):
    """Отмена заказа"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if request.method == 'POST':
        if order.can_cancel():
            order.cancel()
            messages.success(request, f'Заказ №{order.id} успешно отменен')
        else:
            messages.error(request, 'Этот заказ нельзя отменить')

        return redirect('orders:order_detail', order_id=order.id)

    return redirect('orders:order_detail', order_id=order.id)


@login_required
def buy_now(request, product_id):
    """Быстрая покупка одного товара.

    Теперь НЕ создаёт заказ сразу, а откладывает покупку в сессию
    и редиректит на страницу оформления (create_order), где пользователь
    подтверждает данные и переходит к оплате.
    """
    product = get_object_or_404(Product, id=product_id, available=True)

    if request.method != 'POST':
        return redirect(
            'products:product_detail',
            category_slug=product.category.slug,
            product_slug=product.slug
        )

    # ===== Проверка оферты =====
    from apps.accounts.models import Offer
    active_offer = Offer.objects.filter(is_active=True).first()

    if active_offer and request.user.offer_accepted_id != active_offer.id:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            from django.urls import reverse
            return JsonResponse({
                'success': False,
                'offer_required': True,
                'offer_url': reverse('accounts:offer_detail', args=[active_offer.id]),
                'profile_url': reverse('accounts:profile'),
                'message': 'Для оформления заказа необходимо принять оферту.',
            }, status=200)

        messages.warning(request, 'Для оформления заказа необходимо принять оферту.')
        return redirect('accounts:profile')

    # ===== Проверка согласия на обработку ПД =====
    if not request.user.personal_data_consent:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            from django.urls import reverse
            return JsonResponse({
                'success': False,
                'consent_required': True,
                'profile_url': reverse('accounts:profile'),
                'message': 'Для оформления заказа необходимо согласие на обработку персональных данных.',
            }, status=200)

        messages.warning(
            request,
            'Для оформления заказа необходимо согласие на обработку персональных данных. '
            'Дайте согласие в личном кабинете.'
        )
        return redirect('accounts:profile')

    # ===== Собираем данные =====
    size = request.POST.get('size', '')
    delivery_method = request.POST.get('delivery_method', '')
    delivery_point = request.POST.get('delivery_point', '{}')
    try:
        quantity = int(request.POST.get('quantity', 1) or 1)
    except (TypeError, ValueError):
        quantity = 1
    if quantity < 1:
        quantity = 1

    try:
        point_data = json.loads(delivery_point) if delivery_point else {}
    except Exception:
        point_data = {}

    # ===== Складываем "быструю покупку" в сессию =====
    request.session['buy_now'] = {
        'product_id': product.id,
        'size': size,
        'quantity': quantity,  # ← было 1
        'delivery_method': delivery_method,
        'delivery_point': point_data,
    }
    request.session.modified = True

    # ===== AJAX-ответ: клиент сам перейдёт на страницу оформления =====
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        from django.urls import reverse
        return JsonResponse({
            'success': True,
            'redirect_url': reverse('orders:create_order') + '?from=buy-now',
        })

    return redirect('orders:create_order')

@login_required
def add_review(request):
    """
    Страница добавления отзыва на товары из доставленного заказа
    """
    order_id = request.GET.get('order_id')

    if not order_id:
        messages.error(request, 'Заказ не указан')
        return redirect('orders:order_list')

    order = get_object_or_404(Order, id=order_id, user=request.user)

    # Проверяем, что заказ доставлен
    if order.status != 'delivered':
        messages.error(request, 'Отзыв можно оставить только для доставленных заказов')
        return redirect('orders:order_list')

    # Проверяем, есть ли уже отзывы на товары из этого заказа
    existing_reviews = Review.objects.filter(order=order, user=request.user)
    reviewed_product_ids = existing_reviews.values_list('product_id', flat=True)

    # Получаем товары из заказа, на которые еще нет отзывов
    items = order.items.all()
    available_products = []
    for item in items:
        if item.product.id not in reviewed_product_ids:
            available_products.append(item.product)

    if not available_products:
        messages.info(request, 'Вы уже оставили отзывы на все товары из этого заказа')
        return redirect('orders:order_list')

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if not product_id or not rating:
            messages.error(request, 'Заполните все обязательные поля')
            return redirect(f'/orders/add-review/?order_id={order_id}')

        product = get_object_or_404(Product, id=product_id)

        # Проверяем, что товар есть в заказе
        if not order.items.filter(product_id=product_id).exists():
            messages.error(request, 'Товар не найден в заказе')
            return redirect('orders:order_list')

        # Проверяем, что отзыв еще не оставлен
        if Review.objects.filter(product=product, user=request.user, order=order).exists():
            messages.warning(request, 'Отзыв на этот товар уже оставлен')
            return redirect(f'/orders/add-review/?order_id={order_id}')

        review = Review.objects.create(
            product=product,
            user=request.user,
            order=order,
            rating=int(rating),
            comment=comment
        )

        # Обработка прикреплённых файлов
        files = request.FILES.getlist('media')
        for idx, f in enumerate(files):
            content_type = f.content_type or ''
            if content_type.startswith('image/'):
                ReviewMedia.objects.create(
                    review=review,
                    media_type='image',
                    image=f,
                    order=idx,
                )
            elif content_type.startswith('video/'):
                media = ReviewMedia.objects.create(
                    review=review,
                    media_type='video',
                    video=f,
                    order=idx,
                )

        messages.success(request, f'Спасибо за отзыв на "{product.name}"!')

        # Проверяем, остались ли еще товары без отзывов
        remaining_items = order.items.exclude(product_id=product_id)
        remaining_products = []
        for item in remaining_items:
            if item.product.id not in reviewed_product_ids:
                remaining_products.append(item.product)

        if remaining_products:
            return redirect(f'/orders/add-review/?order_id={order_id}')
        else:
            return redirect('orders:order_list')

    context = {
        'order': order,
        'available_products': available_products,
        'existing_reviews': existing_reviews,
    }
    return render(request, 'orders/add_review.html', context)


@login_required
def create_return(request, order_id):
    """Создание заявки на возврат товара из заказа."""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    # ===== Проверки =====
    if not order.can_return:
        messages.error(
            request,
            'Срок подачи заявки на возврат истёк или заказ ещё не доставлен.'
        )
        return redirect('orders:order_list')

    # Разрешаем создавать новую заявку, если есть ещё что возвращать
    if order.returnable_items_count == 0:
        messages.info(request, f'По заказу №{order.id} все товары уже отправлены на возврат.')
        return redirect('orders:order_list')

    # ===== POST — создаём заявку =====
    if request.method == 'POST':
        form = ReturnCreateForm(request.POST)
        if form.is_valid():
            # Создаём Return (фиксируется created = auto_now_add)
            ret = form.save(commit=False)
            ret.order = order
            ret.user = request.user
            ret.status = 'new'
            ret.save()

            # ===== Позиции — выбор отдельных товаров =====
            selected_ids = request.POST.getlist('item_ids')

            # Если ничего не передано — берём все доступные к возврату
            if not selected_ids:
                returnable = order.returnable_items
            else:
                # Ограничиваем: только те, что реально доступны для возврата
                returnable = order.returnable_items.filter(id__in=selected_ids)

            if not returnable.exists():
                messages.error(request, 'Не выбрано ни одного товара для возврата.')
                return redirect('orders:order_list')

            for item in returnable:
                ReturnItem.objects.create(
                    return_request=ret,
                    order_item=item,
                    product=item.product,
                    product_name=item.product.name if item.product else 'Товар удалён',
                    size=getattr(item, 'size', '') or '',
                    price=item.price,
                    quantity=item.quantity,
                )

            # ===== Фото =====
            files = request.FILES.getlist('photos')
            for idx, f in enumerate(files):
                content_type = f.content_type or ''
                if content_type.startswith('image/'):
                    ReturnPhoto.objects.create(
                        return_request=ret,
                        image=f,
                        comment=f'Фото {idx + 1}',
                    )

            # ===== Уведомление админам =====
            try:
                from django.contrib.auth import get_user_model
                from apps.accounts.utils import send_push_safe
                User = get_user_model()
                admins = User.objects.filter(is_staff=True, is_active=True)
                payload = {
                    "head": "↩️ Новая заявка на возврат",
                    "body": f'Заказ №{order.id}, клиент: {request.user.email}',
                    "icon": "/static/icons/icon-192x192.png",
                    "url": f"/admin/orders/return/{ret.id}/change/",
                }
                for admin in admins:
                    send_push_safe(admin, payload)
            except Exception as e:
                print(f'Push error (return): {e}')

            messages.success(
                request,
                f'Заявка на возврат №{ret.id} успешно создана. '
                f'Мы рассмотрим её в течение 1–2 рабочих дней.'
            )
            return redirect('orders:order_list')

        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки в форме.')
    else:
        form = ReturnCreateForm()

    # ===== Считаем доступные для возврата товары =====
    order_items = order.returnable_items.select_related('product').all()

    # Предвыбранные item_ids из URL (при клике «Создать заявку» из модалки)
    preselected_ids = request.GET.getlist('item_ids')
    total_quantity = sum(i.quantity for i in order_items)

    return render(request, 'orders/return_create.html', {
        'order': order,
        'form': form,
        'order_items': order_items,
        'total_quantity': sum(i.quantity for i in order_items),
        'max_photos': 10,
    })