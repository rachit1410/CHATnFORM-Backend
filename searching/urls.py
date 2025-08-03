from django.urls import path
from searching.views import SearchUserAPI

urlpatterns = [
    path('user/', SearchUserAPI.as_view(), name='user')
]
