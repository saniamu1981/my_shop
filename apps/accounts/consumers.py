import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.core.cache import cache
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

        # Помечаем себя «онлайн»
        await self.set_online(True)

        # Помечаем сообщения админа как прочитанные (пользователь открыл чат)
        await self.mark_admin_messages_read()

        # Уведомляем админский чат, что пользователь прочитал
        await self.channel_layer.group_send(
            f'chat_admin_{self.user.id}',
            {'type': 'messages_read', 'reader': 'user'}
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
            await self.set_online(False)

    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
        except json.JSONDecodeError:
            return

        # Пинг — обновляем «онлайн»-ключ, продлеваем TTL
        if data.get('type') == 'ping':
            await self.set_online(True)
            return

        message_text = (data.get('message') or '').strip()
        if not message_text:
            return

        msg = await self.save_message(self.user.id, 'user', message_text)

        # Отправляем в группу пользователя (чтобы пользователь увидел своё сообщение)
        await self.channel_layer.group_send(
            self.group_name,
            {'type': 'chat_message', 'message': msg}
        )
        # И в группу админа (чтобы админ увидел)
        await self.channel_layer.group_send(
            f'chat_admin_{self.user.id}',
            {'type': 'chat_message', 'message': msg}
        )

    async def chat_message(self, event):
        msg = event['message']

        # Пометка прочитанным — только для сообщений от админа
        # И только если админ онлайн
        if msg.get('sender') == 'admin':
            admin_online = await self.is_admin_online(msg['id'])
            if admin_online:
                await self.mark_message_read(msg['id'])
                await self.channel_layer.group_send(
                    f'chat_admin_{self.user.id}',
                    {'type': 'messages_read', 'reader': 'user'}
                )

        await self.send(text_data=json.dumps(msg))

    async def messages_read(self, event):
        """Админ прочитал сообщения пользователя."""
        read_ids = await self.get_my_read_ids(self.user.id, 'user')
        await self.send(text_data=json.dumps({
            'type': 'read_update',
            'read_ids': read_ids,
        }))

    # ============ DB-хелперы ============

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
    def mark_message_read(self, message_id):
        ChatMessage.objects.filter(id=message_id, is_read=False).update(is_read=True)

    @database_sync_to_async
    def get_my_read_ids(self, user_id, sender):
        return list(
            ChatMessage.objects.filter(
                user_id=user_id, sender=sender, is_read=True
            ).values_list('id', flat=True)
        )

    # ============ Redis-хелперы ============

    @database_sync_to_async
    def set_online(self, value):
        key = f'online_user_{self.user.id}'
        if value:
            cache.set(key, True, timeout=60)
        else:
            cache.delete(key)

    @database_sync_to_async
    def is_admin_online(self, message_id):
        """
        Проверяем, онлайн ли админ, с которым переписывается пользователь.
        Для этого смотрим, есть ли активный WebSocket-ключ в Redis по группе
        chat_admin_<id>. Но проще — считать админа онлайн всегда, если он
        подключён к админскому consumer'у. Реализуем через ключ online_admin_<user_id>.
        """
        key = f'online_admin_{self.user.id}'
        return bool(cache.get(key))