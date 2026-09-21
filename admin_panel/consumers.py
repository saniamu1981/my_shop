import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from apps.accounts.models import ChatMessage


class AdminChatConsumer(AsyncWebsocketConsumer):
    """
    WebSocket-чат админа с конкретным пользователем.
    Группа: chat_admin_<user_id>
    """

    async def connect(self):
        self.admin = self.scope['user']

        if not self.admin.is_authenticated or not self.admin.is_staff:
            await self.close()
            return

        self.user_id = int(self.scope['url_route']['kwargs']['user_id'])
        self.group_name = f'chat_admin_{self.user_id}'

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        # Помечаем сообщения пользователя как прочитанные
        await self.mark_user_messages_read()

        # Уведомляем пользовательский чат, что админ прочитал
        await self.channel_layer.group_send(
            f'chat_user_{self.user_id}',
            {'type': 'messages_read', 'reader': 'admin'}
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

        msg = await self.save_message(self.user_id, 'admin', message_text)

        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat_message', 'message': msg}
        )
        await self.channel_layer.group_send(
            f'chat_user_{self.user_id}',
            {'type': 'chat_message', 'message': msg}
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps(event['message']))

    async def messages_read(self, event):
        read_ids = await self.get_my_read_ids(self.user_id, 'admin')
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
    def mark_user_messages_read(self):
        ChatMessage.objects.filter(
            user_id=self.user_id, sender='user', is_read=False
        ).update(is_read=True)

    @database_sync_to_async
    def get_my_read_ids(self, user_id, sender):
        return list(
            ChatMessage.objects.filter(
                user_id=user_id, sender=sender, is_read=True
            ).values_list('id', flat=True)
        )