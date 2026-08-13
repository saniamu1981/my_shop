from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from .models import Category, Product, Favorite


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

    is_favorite = False
    favorites_count = 0
    if request.user.is_authenticated:
        is_favorite = Favorite.objects.filter(user=request.user, product=product).exists()
        favorites_count = Favorite.objects.filter(user=request.user).count()

    return render(request, 'products/product_detail.html', {
        'product': product,
        'main_image': main_image,
        'all_images': images,
        'videos': videos,
        'is_favorite': is_favorite,
        'favorites_count': favorites_count,
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