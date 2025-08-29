# kafka_consumer.py
import json
from django.core.management.base import BaseCommand
from django.conf import settings
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from confluent_kafka import Consumer, KafkaError


class Command(BaseCommand):
    help = 'Runs a Kafka consumer to push messages to Django Channels.'

    def handle(self, *args, **options):
        self.stdout.write("Starting Kafka consumer")
        channel_layer = get_channel_layer()

        conf = {
            "bootstrap.servers": settings.KAFKA_BROKER_URL,
            "group.id": "django_websocket_consumer_group",
            "enable.auto.commit": False,  # <- let it commit offsets
            "auto.offset.reset": "latest"
        }
        consumer = Consumer(**conf)
        consumer.subscribe([settings.KAFKA_TOPIC])

        try:
            while True:
                msg = consumer.poll(timeout=1.0)
                if msg is None:
                    self.stdout.write("No message polled this cycle.")
                    continue
                if msg.error():
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        self.stdout.write(f"End of partition reached {msg.topic()}/{msg.partition()}")
                    else:
                        self.stdout.write(f"Kafka consumer error: {msg.error()}")
                    continue

                message_value = msg.value().decode('utf-8')
                data = json.loads(message_value)

                async_to_sync(channel_layer.group_send)(
                    data["group_id"],
                    {
                        "type": "send_realtime_data",
                        "data": data
                    }
                )
                consumer.commit(asynchronous=False)
        except KeyboardInterrupt:
            self.stdout.write("Kafka consumer intrrupted. Shutting down...")
        except Exception as e:
            self.stdout.write(f"An unexpected error occurred in kafka consumer: {e}")
        finally:
            consumer.close()
            self.stdout.write("kafka consumer stopped.")
