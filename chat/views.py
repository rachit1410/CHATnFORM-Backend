from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import generics
# from chat.kafka_utils import send_realtime_event
# from django.utils import timezone
# from django.conf import settings
from chat.serializers import GroupSerialiazer
from chat.models import ChatGroup
import logging
from uuid import UUID
logger = logging.getLogger(__name__)


class CreateGroupAPI(APIView):

    def post(self, request):
        try:
            data = request.data
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
            group = ChatGroup.objects.get(uid=group_id, group_owner=user)
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
            group = ChatGroup.objects.get(uid=group_id, created_by=user)
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


# def post(self, request):
#     data = {'event_type': 'user_action', 'user_id': request.user.id, 'timestamp': str(timezone.now())}
#     send_realtime_event(settings.KAFKA_TOPIC, data)
#     return Response({'status': 'event sent'})
