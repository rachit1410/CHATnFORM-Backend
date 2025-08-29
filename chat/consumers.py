import json
import uuid
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.exceptions import StopConsumer
from asgiref.sync import sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.core.cache import cache
from cryptography.fernet import Fernet
from chat.kafka_utils import send_realtime_event
from chat.utils import is_member

logger = logging.getLogger(__name__)
fernet = Fernet(settings.FERNET_KEY)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        try:
            self.group_name = self.scope["url_route"]["kwargs"]["group_id"]
            user = self.scope["user"]
            user_id = user.id if user else None

            if not user or not await is_member(self.group_name, user):
                logger.info("Not authorized.")
                await self.close()
                return

            self.user_group = f"user_{user_id}_{self.group_name}"

            # 🔑 Deduplicate: ensure only 1 socket per (user, group)
            cache_key = f"ws_active_{user_id}_{self.group_name}"
            old_channel = cache.get(cache_key)
            if old_channel and old_channel != self.channel_name:
                # tell old socket to disconnect
                await self.channel_layer.send(
                    old_channel,
                    {"type": "force_disconnect"}
                )

            # save current channel
            cache.set(cache_key, self.channel_name, timeout=3600)

            # Join groups
            await self.channel_layer.group_add(self.user_group, self.channel_name)
            await self.channel_layer.group_add(self.group_name, self.channel_name)

            await self.accept()
            logger.info("WebSocket connection accepted.")
            await self.send(text_data=json.dumps({"message": "connection made."}))

        except Exception as e:
            logger.exception(f"Error during WebSocket connect: {e}")
            await self.close(code=1011)

    async def receive(self, text_data=None):
        from chat.models import ChatGroup, GroupChat
        User = get_user_model()

        try:
            data = json.loads(text_data)
            sender_id = data.get("sender")
            msg_id = data.get("id") or str(uuid.uuid4())
            group_id = self.group_name

            # Deduplication check (client retries, etc.)
            cache_key = f"chat_msg_{msg_id}"
            if cache.get(cache_key):
                logger.info(f"Duplicate message {msg_id} ignored for group {group_id}")
                return
            cache.set(cache_key, True, timeout=60)

            # Verify membership
            group = await sync_to_async(ChatGroup.objects.get)(
                uid=uuid.UUID(group_id),
                group_members__member__id=sender_id
            )
            sent_by = await sync_to_async(User.objects.get)(id=sender_id)

            raw_message = data.get("message", "") or ""
            encrypted_message = (
                fernet.encrypt(raw_message.encode("utf-8")).decode("utf-8")
                if raw_message else ""
            )

            message_data = {
                "id": msg_id,
                "sender_id": sender_id,
                "sender_name": getattr(sent_by, "name", getattr(sent_by, "username", "")),
                "group_id": group_id,
                "message": encrypted_message,
                "file": data.get("file_url"),
                "message_type": data.get("message_type", "text"),
                "timestamp": timezone.now().isoformat(),
            }

            # Save to DB
            await sync_to_async(GroupChat.objects.create)(
                group=group,
                sent_by=sent_by,
                message_type=message_data["message_type"],
                text_message=encrypted_message,
                file_message=message_data["file"]
            )

            # Publish only to Kafka (no direct echo here)
            await sync_to_async(send_realtime_event)(
                settings.KAFKA_TOPIC,
                message_data,
                origin=self.channel_name  # tag sender channel
            )

        except ChatGroup.DoesNotExist:
            await self.send(text_data=json.dumps(
                {"error": "You are not authorised to message in this group."}
            ))
        except StopConsumer:
            await self.close()
        except Exception as e:
            logger.exception(f"Error during message receive: {e}")
            await self.send(text_data=json.dumps({"error": "Message processing error."}))

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected: {close_code}")
        user = self.scope["user"]
        if user and user.is_authenticated:
            cache_key = f"ws_active_{user.id}_{self.group_name}"
            # Only clear if this channel is the current one
            if cache.get(cache_key) == self.channel_name:
                cache.delete(cache_key)

        await self.channel_layer.group_discard(self.group_name, self.channel_name)
        await self.channel_layer.group_discard(self.user_group, self.channel_name)

    async def send_realtime_data(self, event):
        logger.info("sending message to WebSocket")
        data = event["data"]

        # Skip if this is the origin socket
        if data.get("origin") == self.channel_name:
            return

        try:
            decrypted_msg = None
            if data.get("message"):
                try:
                    decrypted_msg = fernet.decrypt(data["message"].encode("utf-8")).decode("utf-8")
                except Exception:
                    decrypted_msg = data["message"]

            await self.send(text_data=json.dumps({
                "id": data.get("id"),
                "type": data.get("message_type", "text"),
                "message": decrypted_msg,
                "sender_id": data.get("sender_id"),
                "sender_name": data.get("sender_name"),
                "file": data.get("file"),
                "timestamp": data.get("timestamp")
            }))
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            await self.close(code=1011)

    # 🔑 Handle duplicate connection cleanup
    async def force_disconnect(self, event):
        logger.info("Force disconnecting duplicate socket")
        await self.close()
