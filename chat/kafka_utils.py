import json
from django.conf import settings
from confluent_kafka import Producer


def get_kafka_producer():
    conf = {"bootstrap.servers": settings.KAFKA_BROKER_URL}
    return Producer(**conf)


def send_realtime_event(topic, message_data):
    producer = get_kafka_producer()
    producer.produce(topic, value=json.dumps(message_data).encode('utf-8'))
    producer.flush()
