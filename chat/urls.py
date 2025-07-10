from django.urls import path
from chat.views import (
    CreateGroupAPI,
    ListGroupsAPI,
    AddMemberAPI,
    MessageAPI
)

urlpatterns = [
    path("create-group/", CreateGroupAPI.as_view()),
    path("list-groups/", ListGroupsAPI.as_view()),
    path("ass-member/", AddMemberAPI.as_view()),
    path("messages/", MessageAPI.as_view()),
]
