import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.accounts.models import ChatMessage
from apps.accounts.utils import send_push_safe
from django.contrib.auth import get_user_model


class AdminChatConsumer(AsyncWebsocketConsumer):
    """Админский чат. Группа: chat_admin_<user_id>"""

    async def connect(self):
        self.admin = self.scope['user']

        if not self.admin.is_authenticated or not self.admin.is_staff:
            await self.close()
            return

        self.user_id = int(self.scope['url_route']['kwargs']['user_id'])
        self.group_name = f'chat_admin_{self.user_id}'
        self.in_focus = False

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # НЕ помечаем здесь. Пометка произойдёт при получении 'focus'
        # от клиента, когда вкладка действительно видима.

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        # Обработка focus / blur
        if data.get('type') == 'focus':
            self.in_focus = True
            # Помечаем все сообщения пользователя прочитанными
            await self.mark_messages_read(sender='user')
            await self.channel_layer.group_send(
                f'chat_user_{self.user_id}',
                {'type': 'messages_read'}
            )
            return
        if data.get('type') == 'blur':
            self.in_focus = False
            return

        text = (data.get('message') or '').strip()
        if not text:
            return

        msg = await self.save_message(self.user_id, 'admin', text)

        # Уведомление пользователю, что админ ответил
        await self.notify_user(msg)

        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat_message', 'message': msg}
        )
        await self.channel_layer.group_send(
            f'chat_user_{self.user_id}',
            {'type': 'chat_message', 'message': msg}
        )

    async def chat_message(self, event):
        msg = event['message']

        # Пометка прочитанным — только если админ в фокусе
        if msg.get('sender') == 'user' and self.in_focus:
            await self.mark_one_read(msg['id'])
            await self.channel_layer.group_send(
                f'chat_user_{self.user_id}',
                {'type': 'messages_read'}
            )

        await self.send(text_data=json.dumps(msg))

    async def messages_read(self, event):
        read_ids = await self.get_read_ids(sender='admin')
        await self.send(text_data=json.dumps({
            'type': 'read_update',
            'read_ids': read_ids,
        }))

    @database_sync_to_async
    def notify_user(self, msg):
        User = get_user_model()
        try:
            target_user = User.objects.get(id=self.user_id)
        except User.DoesNotExist:
            return

        payload = {
            "head": "💬 Ответ поддержки",
            "body": msg['message'][:80],
            "icon": "/static/icons/icon-192x192.png",
            "url": "/profile/chat/",
        }
        send_push_safe(target_user, payload)

    @database_sync_to_async
    def save_message(self, user_id, sender, text):
        msg = ChatMessage.objects.create(user_id=user_id, sender=sender, message=text)
        return {
            'id': msg.id,
            'sender': msg.sender,
            'message': msg.message,
            'created': msg.created.strftime('%d.%m.%Y %H:%M'),
            'is_read': msg.is_read,
        }

    @database_sync_to_async
    def mark_messages_read(self, sender):
        ChatMessage.objects.filter(
            user_id=self.user_id, sender=sender, is_read=False
        ).update(is_read=True)

    @database_sync_to_async
    def mark_one_read(self, message_id):
        ChatMessage.objects.filter(id=message_id, is_read=False).update(is_read=True)

    @database_sync_to_async
    def get_read_ids(self, sender):
        return list(
            ChatMessage.objects.filter(
                user_id=self.user_id, sender=sender, is_read=True
            ).values_list('id', flat=True)
        )