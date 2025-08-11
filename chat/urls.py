from django.urls import path
from chat.views import (
    CreateGroupAPI,
    ListGroupsAPI,
    MemberAPI,
    MessageAPI,
    RefreshApi
)

urlpatterns = [
    path("create-group/", CreateGroupAPI.as_view()),
    path("list-groups/", ListGroupsAPI.as_view()),
    path("members/", MemberAPI.as_view()),
    path("messages/", MessageAPI.as_view()),
    path("custom-refresh/", RefreshApi.as_view())
]
