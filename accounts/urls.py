from django.urls import path
from accounts.views import (
    RegisterApiView,
    VerifyEmail,
    LoginApiView,
    VarifyToCP,
    ChangePassword
)
from rest_framework_simplejwt.views import (
    TokenRefreshView,
)

urlpatterns = [
    path("register/", RegisterApiView.as_view()),
    path("varify-email/", VerifyEmail.as_view()),
    path("login-n-logout/", LoginApiView.as_view()),
    path('token/refresh/', TokenRefreshView.as_view()),
    path('forgot-password/', VarifyToCP.as_view()),
    path('change-password/', ChangePassword.as_view()),
]
