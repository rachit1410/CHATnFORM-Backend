from chat.models import Member, Image
from django.contrib.auth import get_user_model
import json
import logging
from rest_framework import serializers
from celery import shared_task
logger = logging.getLogger(__name__)


@shared_task
def finalize_group_creation(data, serializer):
    User = get_user_model()
    profile_image_list = data.pop('group_profile', None)
    profile_image = None
    if profile_image_list and isinstance(profile_image_list, list) and len(profile_image_list) > 0:
        profile_image = profile_image_list[0]
    if profile_image:
        image = Image.objects.create(image=profile_image)
    else:
        image = None
    owner = serializer.instance.group_owner
    Member.objects.create(
        member=owner,
        group=serializer.instance,
        role="admin"
    )
    if image:
        serializer.instance.group_profile = image
        serializer.instance.save()
    if member_ids_raw := data.get('memberIds'):
        try:
            data['memberIds'] = json.loads(member_ids_raw)
            if not isinstance(data['memberIds'], list):
                data['memberIds'] = [data['memberIds']]

            members = []
            for member_id in data['memberIds']:
                member = Member(
                    member=User.objects.get(id=member_id),
                    group=serializer.instance,
                    role="regular"
                )
                members.append(member)
            Member.objects.bulk_create(members)

        except (json.JSONDecodeError, IndexError) as e:
            logger.error(f"Error processing member IDs: {e}")
            print(f"Error processing member IDs: {e}")
            raise serializers.ValidationError("Invalid member IDs format.")
    else:
        logger.info("No member IDs provided, skipping member creation.")
        print("No member IDs provided, skipping member creation.")
