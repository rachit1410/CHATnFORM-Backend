from rest_framework import serializers
from chat.models import ChatGroup, Member, JoinRequest, GroupChat, Image
from accounts.serializers import CNFUserSerializer


class ImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = Image()
        fields = ['image']


class GroupSerialiazer(serializers.ModelSerializer):
    # group_profile = ImageSerializer()

    def create(self, validated_data):
        user = validated_data.get("group_owner")
        group = ChatGroup.objects.create(**validated_data)
        Member.objects.create(
            member=user,
            group=group,
            role="admin"
        )
        return group

    class Meta:
        model = ChatGroup
        exclude = ['updated_at']


class MemberSerializer(serializers.ModelSerializer):
    group = GroupSerialiazer(many=True)

    class Meta:
        model = Member
        exclude = ['created_at', 'updated_at']


class RequestSerializer(serializers.ModelSerializer):
    group = GroupSerialiazer()
    cnf_user = CNFUserSerializer()

    class Meta:
        model = JoinRequest
        exclude = ['updated_at']


class ChatSerializer(serializers.ModelSerializer):
    group = ChatGroup()

    class Meta:
        model = GroupChat
        exclude = ['updated_at']
