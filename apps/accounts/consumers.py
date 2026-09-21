import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import ChatMessage


class ChatConsumer(AsyncWebsocketConsumer):
    """Пользовательский чат. Группа: chat_user_<user_id>"""

    async def connect(self):
        self.user = self.scope['user']

        if not self.user.is_authenticated:
            await self.close()
            return

        self.group_name = f'chat_user_{self.user.id}'
        self.in_focus = False   # ← добавили

        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.mark_messages_read(sender='admin')
        await self.channel_layer.group_send(
            f'chat_admin_{self.user.id}',
            {'type': 'messages_read'}
        )

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
            await self.mark_messages_read(sender='admin')
            await self.channel_layer.group_send(
                f'chat_admin_{self.user.id}',
                {'type': 'messages_read'}
            )
            return
        if data.get('type') == 'blur':
            self.in_focus = False
            return

        text = (data.get('message') or '').strip()
        if not text:
            return

        msg = await self.save_message(self.user.id, 'user', text)

        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat_message', 'message': msg}
        )
        await self.channel_layer.group_send(
            f'chat_admin_{self.user.id}',
            {'type': 'chat_message', 'message': msg}
        )

    async def chat_message(self, event):
        msg = event['message']

        # Пометка прочитанным — только если пользователь в фокусе
        if msg.get('sender') == 'admin' and self.in_focus:   # ← добавили in_focus
            await self.mark_one_read(msg['id'])
            await self.channel_layer.group_send(
                f'chat_admin_{self.user.id}',
                {'type': 'messages_read'}
            )

        await self.send(text_data=json.dumps(msg))

    async def messages_read(self, event):
        read_ids = await self.get_read_ids(sender='user')
        await self.send(text_data=json.dumps({
            'type': 'read_update',
            'read_ids': read_ids,
        }))

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
            user_id=self.user.id, sender=sender, is_read=False
        ).update(is_read=True)

    @database_sync_to_async
    def mark_one_read(self, message_id):
        ChatMessage.objects.filter(id=message_id, is_read=False).update(is_read=True)

    @database_sync_to_async
    def get_read_ids(self, sender):
        return list(
            ChatMessage.objects.filter(
                user_id=self.user.id, sender=sender, is_read=True
            ).values_list('id', flat=True)
        )