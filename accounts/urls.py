from django.urls import path
from accounts.views import (
    RegisterApiView,
    VerifyEmail,
    LoginApiView,
    VarifyToCP,
    ChangePassword,
    SendOTP,
    GetUserAPI
)

urlpatterns = [
    path("register/", RegisterApiView.as_view()),
    path("send-otp/", SendOTP.as_view()),
    path("verify-email/", VerifyEmail.as_view()),
    path("jwt/", LoginApiView.as_view()),
    path("me/", GetUserAPI.as_view()),
    path('forgot-password/', VarifyToCP.as_view()),
    path('change-password/', ChangePassword.as_view()),
]
