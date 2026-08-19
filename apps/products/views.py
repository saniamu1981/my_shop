from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Category, Product, Favorite, Review
from django.conf import settings
from apps.orders.models import Order


def product_list(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True).order_by('-created')

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    favorites_ids = []
    if request.user.is_authenticated:
        favorites_ids = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)

    return render(request, 'products/product_list.html', {
        'category': category,
        'categories': categories,
        'products': products,
        'favorites_ids': list(favorites_ids),
    })


def product_detail(request, category_slug, product_slug):
    product = get_object_or_404(Product, slug=product_slug, category__slug=category_slug)

    images = product.images.all().order_by('order')
    videos = product.videos.all().order_by('order')

    main_image = images.filter(is_main=True).first()
    if not main_image and product.image:
        main_image = product.image

    # Получаем одобренные отзывы для товара
    reviews = product.reviews.filter(is_approved=True).order_by('-created')
    reviews_count = reviews.count()

    # Средний рейтинг
    average_rating = 0
    if reviews_count > 0:
        from django.db.models import Avg
        average_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0

    is_favorite = False
    favorites_count = 0
    user_review = None
    can_review = False
    has_review = False

    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, product=product).exists()
        favorites_count = Favorite.objects.filter(user=request.user).count()

        # Проверяем, есть ли у пользователя отзыв на этот товар
        user_review = Review.objects.filter(product=product, user=request.user).first()
        if user_review:
            has_review = True

        # Проверяем, может ли пользователь оставить отзыв (если нет отзыва, но есть доставленный заказ)
        if not has_review:
            can_review = Order.objects.filter(
                user=request.user,
                status='delivered',
                items__product=product
            ).exists()

    return render(request, 'products/product_detail.html', {
        'product': product,
        'main_image': main_image,
        'all_images': images,
        'videos': videos,
        'is_favorite': is_favorite,
        'favorites_count': favorites_count,
        'reviews': reviews[:10],
        'reviews_count': reviews_count,
        'average_rating': average_rating,
        'can_review': can_review,
        'has_review': has_review,
        'user_review': user_review,
        'YANDEX_MAPS_API_KEY': settings.YANDEX_MAPS_API_KEY,
    })

@login_required
def toggle_favorite(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    favorite, created = Favorite.objects.get_or_create(user=request.user, product=product)

    if not created:
        favorite.delete()
        is_favorite = False
        message = f'Товар "{product.name}" удален из избранного'
    else:
        is_favorite = True
        message = f'Товар "{product.name}" добавлен в избранное'

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'is_favorite': is_favorite,
            'message': message,
            'favorites_count': Favorite.objects.filter(user=request.user).count()  # <-- Убедитесь, что это есть
        })

    messages.success(request, message)
    return redirect(request.META.get('HTTP_REFERER', 'products:product_list'))


@login_required
def favorite_list(request):
    favorites = Favorite.objects.filter(user=request.user).select_related('product')
    products = [fav.product for fav in favorites]

    paginator = Paginator(products, 12)
    page = request.GET.get('page', 1)
    try:
        products = paginator.page(page)
    except PageNotAnInteger:
        products = paginator.page(1)
    except EmptyPage:
        products = paginator.page(paginator.num_pages)

    favorites_ids = Favorite.objects.filter(user=request.user).values_list('product_id', flat=True)

    return render(request, 'products/favorite_list.html', {
        'products': products,
        'favorites_ids': list(favorites_ids),
    })


@login_required
def add_review(request):
    """Страница добавления отзыва"""
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
    available_products = [item.product for item in items if item.product.id not in reviewed_product_ids]

    if not available_products:
        messages.info(request, 'Вы уже оставили отзывы на все товары из этого заказа')
        return redirect('orders:order_list')

    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if not product_id or not rating:
            messages.error(request, 'Заполните все обязательные поля')
            return redirect('products:add_review') + f'?order_id={order_id}'

        product = get_object_or_404(Product, id=product_id)

        # Проверяем, что товар есть в заказе
        if not order.items.filter(product_id=product_id).exists():
            messages.error(request, 'Товар не найден в заказе')
            return redirect('orders:order_list')

        # Проверяем, что отзыв еще не оставлен
        if Review.objects.filter(product=product, user=request.user, order=order).exists():
            messages.warning(request, 'Отзыв на этот товар уже оставлен')
            return redirect('products:add_review') + f'?order_id={order_id}'

        Review.objects.create(
            product=product,
            user=request.user,
            order=order,
            rating=int(rating),
            comment=comment
        )

        messages.success(request, f'Спасибо за отзыв на "{product.name}"!')

        # Проверяем, остались ли еще товары без отзывов
        remaining_items = order.items.exclude(product_id=product_id)
        remaining_products = [item.product for item in remaining_items if item.product.id not in reviewed_product_ids]

        if remaining_products:
            return redirect(f'/products/add-review/?order_id={order_id}')
        else:
            return redirect('orders:order_list')

    context = {
        'order': order,
        'available_products': available_products,
        'existing_reviews': existing_reviews,
    }
    return render(request, 'products/add_review.html', context)


# apps/products/views.py
@login_required
def get_product_reviews(request, product_id):
    """Получение всех отзывов для товара (AJAX)"""
    product = get_object_or_404(Product, id=product_id)
    reviews = product.reviews.filter(is_approved=True).order_by('-created')

    data = {
        'reviews': [
            {
                'user': r.user.get_full_name() or r.user.email,
                'rating': r.rating,
                'comment': r.comment,
                'date': r.created.strftime('%d.%m.%Y'),
                'is_verified': bool(r.order)
            }
            for r in reviews
        ]
    }
    return JsonResponse(data)


@login_required
def edit_review(request, product_id):
    """Редактирование отзыва"""
    product = get_object_or_404(Product, id=product_id)
    review = get_object_or_404(Review, product=product, user=request.user)

    if request.method == 'POST':
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if not rating:
            messages.error(request, 'Пожалуйста, поставьте оценку')
            return redirect('products:edit_review', product_id=product_id)

        review.rating = int(rating)
        review.comment = comment
        review.save()

        messages.success(request, f'Отзыв на "{product.name}" успешно обновлен!')
        return redirect('products:product_detail', category_slug=product.category.slug, product_slug=product.slug)

    context = {
        'product': product,
        'review': review,
    }
    return render(request, 'products/edit_review.html', context)


@login_required
def delete_review(request, review_id):
    """Удаление отзыва"""
    review = get_object_or_404(Review, id=review_id, user=request.user)
    product = review.product

    if request.method == 'POST':
        product_name = product.name
        review.delete()
        messages.success(request, f'Отзыв на "{product_name}" удален')
        return redirect('products:product_detail', category_slug=product.category.slug, product_slug=product.slug)

    return redirect('products:product_detail', category_slug=product.category.slug, product_slug=product.slug)