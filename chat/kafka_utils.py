# kafka_utils.py
import json
import logging
from confluent_kafka import Producer
from django.conf import settings

logger = logging.getLogger(__name__)

producer = Producer({"bootstrap.servers": settings.KAFKA_BROKER_URL})


def delivery_report(err, msg):
    if err:
        logger.error(f"Message delivery failed: {err}")
    else:
        logger.info(f"Delivered to {msg.topic()} [{msg.partition()}] offset {msg.offset()}")


def send_realtime_event(topic, message_data, origin=None):
    if origin:
        message_data["origin"] = origin
    try:
        producer.produce(
            topic,
            value=json.dumps(message_data).encode("utf-8"),
            callback=delivery_report
        )
        # allow background thread to handle delivery callbacks
        producer.poll(0)
    except BufferError as e:
        logger.error(f"Local producer queue is full: {e}")
