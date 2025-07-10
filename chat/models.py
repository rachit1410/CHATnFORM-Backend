from django.db import models
from django.contrib.auth import get_user_model
from chat.choices import GROUP_TYPES, MESSAGE_TYPE, ROLE_CHOICES
import uuid


class Base(models.Model):
    uid = models.UUIDField(default=uuid.uuid4, primary_key=True, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Image(Base):
    image = models.ImageField(upload_to='images')


class ChatGroup(Base):
    User = get_user_model()
    group_owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="my_groups")
    group_name = models.CharField(max_length=255, unique=True)
    group_description = models.TextField(null=True, blank=True)
    group_profile = models.ForeignKey(Image, related_name="group_image", on_delete=models.SET_NULL, null=True, blank=True)
    group_type = models.CharField(max_length=100, choices=GROUP_TYPES)


class JoinRequest(Base):
    User = get_user_model()
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sent_requests")
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="join_requests")


class Member(Base):
    User = get_user_model()
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="group_members")
    member = models.ForeignKey(User, related_name="joined_groups", on_delete=models.CASCADE)
    role = models.CharField(max_length=100, default="regular", choices=ROLE_CHOICES)


class GroupChat(Base):
    User = get_user_model()
    group = models.ForeignKey(ChatGroup, on_delete=models.CASCADE, related_name="group_chats")
    sent_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name="messages", null=True, blank=True)
    message_type = models.CharField(max_length=100, choices=MESSAGE_TYPE)
    text_message = models.TextField(null=True, blank=True)
    image_message = models.ForeignKey(Image, related_name="in_chats", on_delete=models.CASCADE, null=True, blank=True)
