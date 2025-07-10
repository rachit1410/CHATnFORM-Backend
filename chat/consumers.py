import json
from channels.generic.websocket import AsyncWebsocketConsumer
from chat.kafka_utils import send_realtime_event
from asgiref.sync import sync_to_async
from django.conf import settings
from channels.exceptions import StopConsumer
from django.contrib.auth import get_user_model
from django.utils import timezone
import logging
from uuid import UUID
logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        try:
            self.group_name = self.scope["url_route"]["kwargs"]["group_id"]

            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            logger.info("WebSocket connection accepted.")
            await self.send(text_data=json.dumps({
                    "message": "connection made."
                }))

        except Exception as e:
            logger.exception(f"Error during WebSocket connect:{e}")
            await self.close(code=1011)

    async def receive(self, text_data=None):
        from chat.models import ChatGroup, GroupChat
        User = get_user_model()
        try:
            data = json.loads(text_data)
            sender_id = data["sender"]
            group_id = self.group_name

            group = await sync_to_async(ChatGroup.objects.get)(uid=UUID(group_id), group_members__member__id=sender_id)

            sent_by = await sync_to_async(User.objects.get)(id=sender_id)
            message_data = {
                "sender_id": sender_id,
                "group_id": group_id,
                "message": data["message"],
                "message_type": data["message_type"],
                "timestamp": timezone.now().isoformat()
            }
            # uploading messages to database
            await sync_to_async(GroupChat.objects.create)(
                group=group,
                sent_by=sent_by,
                message_type=data["message_type"],
                text_message=data["message"]
            )

            # publishing messages to kafka
            await sync_to_async(send_realtime_event)(
                settings.KAFKA_TOPIC,
                message_data
            )

        except ChatGroup.DoesNotExist:
            logger.error(f"User {sender_id} sent message in unsubscribed group.")
            await self.send(text_data=json.dumps({
                "error": "You are not authorised to message in this group."
            }))
        except StopConsumer:
            logger.info("StopConsumer exception raised, closing WebSocket.")
            await self.close()
        except Exception as e:
            logger.exception(f"Error during message receive: {e}")
            await self.send(text_data=json.dumps({
                "error": "An error occurred while processing your message."
            }))

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected with code: {close_code}")
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name
        )

    async def send_realtime_data(self, event):
        logger.info("Sending realtime data in the group.")
        data = event["data"]
        await self.send(json.dumps(
            {
                "type": "text",
                "message": data
            }
        ))
