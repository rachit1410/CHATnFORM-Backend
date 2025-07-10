from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from chat.serializers import GroupSerialiazer, ChatSerializer
from chat.models import ChatGroup, Member, GroupChat
import logging
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from chat.permissions import IsMember
from uuid import UUID
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
logger = logging.getLogger(__name__)


class CreateGroupAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            data = request.data
            data["group_owner"] = request.user.pk
            serializer = GroupSerialiazer(data=data)

            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "status": True,
                        "message": "group created successfully.",
                        "data": {}
                    }
                )
            return Response(
                {
                    "status": False,
                    "message": serializer.errors,
                    "data": {}
                }
            )

        except Exception as e:
            logger.error(f"an unaxpected error occurred while creating group: {e}")
            return Response(
                {
                    "status": False,
                    "message": "something went wrong.",
                    "data": {}
                }
            )

    def patch(self, request, *args, **kwargs):
        user = request.user
        group_id = UUID(request.data.get('group_id'))

        try:
            group = ChatGroup.objects.get(
                uid=group_id,
                member__member=user,
                member__role="admin"
            )
            serializer = GroupSerialiazer(group, data=request.data, partial=True)

            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "status": True,
                        "message": "group updated successfully.",
                        "data": {}
                    }
                )
            return Response(
                {
                    "status": False,
                    "message": serializer.errors,
                    "data": {}
                }
            )
        except ChatGroup.DoesNotExist:
            return Response(
                {
                    "status": False,
                    "message": "group not found or you do not have permission to update this group.",
                    "data": {}
                }
            )

    def delete(self, request):
        user = request.user
        group_id = UUID(request.data.get('group_id'))
        try:
            group = ChatGroup.objects.get(uid=group_id, group_owner=user)
            group.delete()
            return Response(
                {
                    "status": True,
                    "message": "group deleted successfully.",
                    "data": {}
                }
            )
        except ChatGroup.DoesNotExist:
            return Response(
                {
                    "status": False,
                    "message": "group not found or you do not have permission to delete this group.",
                    "data": {}
                }
            )


class ListGroupsAPI(generics.ListAPIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerialiazer

    def get_queryset(self):
        user = self.request.user
        return ChatGroup.objects.filter(member__member=user)

    def get(self, request, *args, **kwargs):
        try:
            return super().get(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"an unexpected error occurred while listing joined groups: {e}")
            return Response(
                {
                    "status": False,
                    "message": "something went wrong.",
                    "data": {}
                }
            )


class AddMemberAPI(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        User = get_user_model()
        try:
            data = request.data
            group = ChatGroup.objects.filter(
                uid=UUID(data.get("group_id")),
                member__member=request.user,
                member__role='admin'
            )

            user_ids_list = data.get("members")

            for user_id in user_ids_list:
                user = User.objects.get(id=user_id)
                Member.objects.create(member=user, group=group)
                logger.info(f"Added member {user.email} in group.")
            logger.info("Successfully added members in group.")
            return Response(
                {
                    "status": True,
                    "message": "members added to group.",
                    "data": {}
                }
            )
        except User.DoesNotExist:
            return Response(
                {
                    "status": False,
                    "message": "User does not exists.",
                    "data": {}
                }
            )
        except Exception as e:
            logger.error(f"An unexpected error occured: {e}")
            return Response(
                {
                    "status": False,
                    "message": "something went wrong.",
                    "data": {}
                }
            )


class MessageAPI(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsMember]
    queryset = GroupChat.objects.all()
    serializer_class = ChatSerializer

    def get_queryset(self):
        group_id = UUID(self.request.GET.get("group"))
        return self.queryset.filter(group__uid=group_id)
