from .models import ChatMessage
from .models import Offer


def unread_chat_count(request):
    """
    Возвращает количество непрочитанных сообщений для текущего пользователя.
    - Для обычного пользователя: ответы админа, которые он ещё не открыл.
    - Для staff/superuser: сообщения пользователей, которые админ ещё не открыл.
    """
    if not request.user.is_authenticated:
        return {'chat_unread_count': 0}

    if request.user.is_staff or request.user.is_superuser:
        # Админу — сколько всего непрочитанных сообщений от пользователей
        count = ChatMessage.objects.filter(sender='user', is_read=False).count()
    else:
        # Пользователю — сколько ответов админа он не открыл
        count = ChatMessage.objects.filter(
            user=request.user, sender='admin', is_read=False
        ).count()

    return {'chat_unread_count': count}

def offer_status(request):
    """Передаёт во все шаблоны active_offer и флаг offer_accepted."""
    if not request.user.is_authenticated:
        return {
            'active_offer': None,
            'offer_accepted': False,
        }

    active_offer = Offer.objects.filter(is_active=True).first()
    offer_accepted = bool(
        active_offer and request.user.offer_accepted_id == active_offer.id
    )
    return {
        'active_offer': active_offer,
        'offer_accepted': offer_accepted,
    }