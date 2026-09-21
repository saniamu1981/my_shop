import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage


class ChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket-чат пользователя с поддержкой.
    Группа: chat_user_<user_id>
    """

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f'chat_user_{self.user.id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Помечаем сообщения от админа как прочитанные
        await self.mark_admin_messages_read()

        # Уведомляем админский чат, что пользователь прочитал
        await self.channel_layer.group_send(
            f'chat_admin_{self.user.id}',
            {'type': 'messages_read', 'reader': 'user'}
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        message_text = (data.get('message') or '').strip()
        if not message_text:
            return

        msg = await self.save_message(self.user.id, 'user', message_text)

        # Рассылаем сообщение в группу пользователя
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat_message', 'message': msg}
        )

        # И в группу админа — чтобы админ увидел мгновенно
        await self.channel_layer.group_send(
            f'chat_admin_{self.user.id}',
            {'type': 'chat_message', 'message': msg}
        )

    async def chat_message(self, event):
        msg = event['message']

        if msg.get('sender') == 'admin':  # ← проверка
            await self.mark_message_read(msg['id'])
            await self.channel_layer.group_send(
                f'chat_admin_{self.user.id}',
                {'type': 'messages_read', 'reader': 'user'}
            )

        await self.send(text_data=json.dumps(msg))

    @database_sync_to_async
    def mark_message_read(self, message_id):
        ChatMessage.objects.filter(id=message_id, is_read=False).update(is_read=True)

    async def messages_read(self, event):
        """Сообщение о том, что собеседник прочитал наши сообщения."""
        read_ids = await self.get_my_read_ids(self.user.id, 'user')
        await self.send(text_data=json.dumps({
            'type': 'read_update',
            'read_ids': read_ids,
        }))

    @database_sync_to_async
    def save_message(self, user_id, sender, text):
        msg = ChatMessage.objects.create(
            user_id=user_id, sender=sender, message=text
        )
        return {
            'id': msg.id,
            'sender': msg.sender,
            'message': msg.message,
            'created': msg.created.strftime('%d.%m.%Y %H:%M'),
            'is_read': msg.is_read,
        }

    @database_sync_to_async
    def mark_admin_messages_read(self):
        ChatMessage.objects.filter(
            user_id=self.user.id, sender='admin', is_read=False
        ).update(is_read=True)

    @database_sync_to_async
    def get_my_read_ids(self, user_id, sender):
        return list(
            ChatMessage.objects.filter(
                user_id=user_id, sender=sender, is_read=True
            ).values_list('id', flat=True)
        )