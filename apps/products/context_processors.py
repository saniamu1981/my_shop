from .models import Favorite

def favorites_count(request):
    """Контекстный процессор для количества избранных товаров"""
    if request.user.is_authenticated:
        count = Favorite.objects.filter(user=request.user).count()
        return {
            'favorites_count': count
        }
    return {'favorites_count': 0}