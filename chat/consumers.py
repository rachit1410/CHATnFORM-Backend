import json
from channels.generic.websocket import AsyncWebsocketConsumer
from chat.kafka_utils import send_realtime_event
from asgiref.sync import sync_to_async
from django.conf import settings
from channels.exceptions import StopConsumer
# from chat.models import GroupChat, ChatGroup
# from django.contrib.auth import get_user_model
from django.utils import timezone
# from uuid import UUID
import logging
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
        # User = get_user_model()
        try:
            data = json.loads(text_data)
            message_data = {
                "sender_id": data["sender"],
                "group_id": data["group"],
                "message": data["message"].encode("utf-8"),
                "message_type": data["message_type"],
                "timestamp": timezone.now().isoformat()
            }

            # await sync_to_async(GroupChat.objects.create)(
            #     group=ChatGroup.objects.get(uuid=UUID(data["group"])),
            #     sent_by=User.objects.get(uuid=UUID(data["sender"])),
            #     message_type=data["message_type"],
            #     text_message=data["message"]
            # )

            await sync_to_async(send_realtime_event)(
                settings.KAFKA_TOPIC,
                message_data
            )

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
