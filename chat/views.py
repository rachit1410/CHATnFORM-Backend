from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
from chat.serializers import GroupSerialiazer, ChatSerializer, MemberSerializer
from chat.models import ChatGroup, Member, GroupChat
import logging
from rest_framework.permissions import IsAuthenticated
from chat.permissions import IsMember
from uuid import UUID
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework import status
from chat.tasks import finalize_group_creation
logger = logging.getLogger()


class CreateGroupAPI(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            logger.info("post method called in CreateGroupAPI")
            data = request.data.copy()
            data["group_owner"] = request.user.pk
            serializer = GroupSerialiazer(data=data)
            if serializer.is_valid():
                logger.info("serializer is valid")
                serializer.save()
                finalize_group_creation(data, serializer)
                return Response(
                    {
                        "status": True,
                        "message": "group created successfully.",
                        "data": {}
                    }
                )
            print("serializer is not valid")
            logger.error(f"serializer errors: {serializer.errors}")
            return Response(
                {
                    "status": False,
                    "message": serializer.errors,
                    "data": {}
                }
            )

        except Exception as e:
            logger.error(f"an unaxpected error occurred while creating group: {e}")
            print(f"an unexpected error occurred while creating group: {e}")
            return Response(
                {
                    "status": False,
                    "message": "something went wrong.",
                    "data": {}
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
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
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerialiazer
    queryset = ChatGroup.objects.all()

    def get_queryset(self):
        user = self.request.user
        return self.queryset.filter(group_members__member=user)

    def get(self, request, *args, **kwargs):
        try:
            queryset = self.get_queryset()
            serializer = self.serializer_class(queryset, many=True)
            data = serializer.data
            return Response(
                {
                    "status": True,
                    "message": "Info : groups fetched.",
                    "data": data
                }
            )
        except Exception as e:
            logger.error(f"an unexpected error occurred while listing joined groups: {e}")
            return Response(
                {
                    "status": False,
                    "message": "something went wrong.",
                    "data": {}
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MemberAPI(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        group_id = request.GET.get("group")
        if not group_id:
            logger.error("error: group_id not provided")
            return Response(
                {
                    "status": False,
                    "message": "error: group_id not provided.",
                    "data": {}
                }
            )
        try:
            group = ChatGroup.objects.get(uid=UUID(group_id), group_members__member=request.user)
            members = Member.objects.filter(group=group)

            serializer = MemberSerializer(members, many=True)
            return Response(
                {
                    "status": True,
                    "message": "Members fetched.",
                    "data": {
                        "members": serializer.data
                    }
                }
            )
        except ChatGroup.DoesNotExist:
            logger.error("error: invalid group id provided.")
            return Response(
                {
                    "status": False,
                    "message": "Group does not exists.",
                    "data": {}
                }
            )

        except Exception as e:
            logger.error(f"an unexpected error occurred while getting members: {e}")
            return Response(
                {
                    "status": False,
                    "message": "something went wrong.",
                    "data": {}
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def post(self, request):
        User = get_user_model()
        try:
            data = request.data
            try:
                group = ChatGroup.objects.get(
                    uid=UUID(data.get("group_id")),
                    member__member=request.user,
                    member__role='admin'
                )
            except ChatGroup.DoesNotExist:
                return Response(
                    {
                        "status": False,
                        "message": "Group does not exist or you don't have admin rights.",
                        "data": {}
                    }
                )

            user_ids_list = data.get("members")

            for user_id in user_ids_list:
                user = User.objects.get(id=user_id)
                Member.objects.create(member=user, group=group)
                logger.info(f"Added member {user.pk} in group.")
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
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class MessageAPI(generics.ListAPIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated, IsMember]
    queryset = GroupChat.objects.all()
    serializer_class = ChatSerializer

    def get_queryset(self):
        group_id = UUID(self.request.GET.get("group"))
        return self.queryset.filter(group__uid=group_id)


class RefreshApi(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(
            {
            "status": True,
            "message": "token refreshed",
            "data": {}
        }
        )

