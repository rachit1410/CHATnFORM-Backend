import logging
from rest_framework.views import APIView
from accounts.serializers import UserRegisterSerializer, UserLoginSerializer
from django.contrib.auth import get_user_model, authenticate
from rest_framework.response import Response
from accounts.utils import generate_otp, is_verified, varify_otp, validate_new_passsword
from django.core.cache import cache
from accounts.models import VerifiedEmail
from rest_framework_simplejwt.tokens import RefreshToken
from accounts.tasks import send_otp
logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterApiView(APIView):

    def post(self, request):
        try:
            data = request.data
            email = data.get("email")
            if not is_verified(email):
                return Response(
                    {
                        "status": False,
                        "message": "email not verified.",
                        "data": {}
                    }
                )

            serializer = UserRegisterSerializer(data=data)
            if serializer.is_valid():
                serializer.save()
                return Response(
                    {
                        "status": True,
                        "message": "acount created.",
                        "data": serializer.data.get("email")
                    }
                )
            logger.warning(f"Registration failed: {serializer.errors}")
            return Response(
                {
                    "status": False,
                    "message": serializer.errors,
                    "data": {}
                }
            )
        except Exception as e:
            logger.error(f"Exception in RegisterApiView: {e}", exc_info=True)
            return Response(
                {
                    "status": False,
                    "message": "something went wrong",
                    "data": {}
                }
            )


class VerifyEmail(APIView):

    def get(self, request):
        try:
            email = request.GET.get("email")
            logger.info(f"Received email verification request for: {email}")

            if is_verified(email):
                logger.info(f"Email already verified: {email}")
                return Response(
                    {
                        "status": True,
                        "message": "email already verified.",
                        "data": {
                            "verified": True
                        }
                    }
                )

            if tries := cache.get(f"blocked:{email}"):
                if tries > 5:
                    logger.warning(f"OTP request throttled for: {email}")
                    return Response(
                        {
                            "status": False,
                            "message": "You hav used all your retries, Please come back after a day.",
                            "data": {}
                        }
                    )

            generate_otp(email)
            otp = cache.get(f"otp:{email}")
            send_otp(
                    subject="OTP for email verification.",
                    message=f'''Your otp for email vaification is {otp}. Enter this otp in otp verification section and hit verify to complete your registration''',
                    email=email
                )
            logger.info(f"Sent OTP email to: {email}")

            return Response(
                {
                    "status": True,
                    "message": "otp sent.",
                    "data": {
                        "verified": False
                    }
                }
            )
        except Exception as e:
            logger.error(f"Exception in VerifyEmail GET: {e}", exc_info=True)
            return Response(
                {
                    "status": False,
                    "message": "something went wrong",
                    "data": {}
                }
            )

    def post(self, request):
        try:
            data = request.data
            if not data:
                data = request.POST
            otp = data.get("otp")
            email = data.get("email")
            logger.info(f"Received OTP verification for: {email}")
            if varify_otp(email=email, otp=otp):
                verify_email = VerifiedEmail.objects.get(email=email)
                verify_email.verified = True
                verify_email.save()
                logger.info(f"Email verified successfully: {email}")
            else:
                logger.warning(f"Invalid OTP for {email}")
                return Response(
                    {
                        "status": False,
                        "message": "incorrect or expired OTP.",
                        "data": {},
                    }
                )
            return Response(
                {
                    "status": True,
                    "message": "email verified",
                    "data": {}
                }
            )
        except Exception as e:
            logger.error(f"Exception in verifyEmail GET: {e}", exc_info=True)
            return Response(
                {
                    "status": False,
                    "message": "something went wrong",
                    "data": {}
                }
            )


class LoginApiView(APIView):

    def post(self, request):
        try:
            data = request.data
            serializer = UserLoginSerializer(data=data)
            if serializer.is_valid():
                email = serializer.validated_data.get("email")
                password = serializer.validated_data.get("password")
                if not is_verified(email=email):
                    logger.error(f"Account exist without email verification: {email}.")
                    return Response(
                        {
                            "status": False,
                            "message": "Your email is not verified. Please verify your email.",
                            "data": {}
                        }
                    )

                authenticated_user = authenticate(request=request, email=email, password=password)

                if authenticated_user is None:
                    logger.warning(f"Attempted login with wrong password on account: {email}")
                    return Response(
                        {
                            "status": False,
                            "message": "incorrect password",
                            "data": {}
                        }
                    )

                refresh = RefreshToken.for_user(authenticated_user)
                return Response(
                    {
                        "status": True,
                        "message": "Logged in successfully",
                        "data": {
                            "refresh_token": str(refresh),
                            "access_token": str(refresh.access_token)
                        }
                    }
                )

            logger.warning(f"Registration failed: {serializer.errors}")
            return Response(
                {
                    "status": False,
                    "message": serializer.errors,
                    "data": {}
                }
            )

        except Exception as e:
            logger.error(f"Exception in verifyEmail GET: {e}", exc_info=True)
            return Response(
                {
                    "status": False,
                    "message": "something went wrong",
                    "data": {}
                }
            )

    def delete(self, request):
        try:
            refresh_token = request.data.get("refresh_token")
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception as e:
                    logger.error(f"Error blacklisting token: {e}", exc_info=True)
                    return Response(
                        {
                            "status": False,
                            "message": "Failed to blacklist token.",
                            "data": {}
                        }
                    )
                return Response(
                    {
                        "status": True,
                        "message": "Logged out successfully.",
                        "data": {}
                    }
                )

            else:
                return Response(
                    {
                        "status": False,
                        "message": "Refresh token required for logout.",
                        "data": {}
                    }
                )
        except Exception as e:
            logger.error(f"Error blacklisting token: {e}", exc_info=True)
            return Response(
                {
                    "status": False,
                    "message": "Failed to logout.",
                    "data": {}
                }
            )


class VarifyToCP(APIView):
    def get(self, request):
        try:
            email = request.data.get("email")

            if not User.objects.filter(email=email).exists():
                return Response(
                    {
                        "status": False,
                        "message": "Account does not exists.",
                        "data": {}
                    }
                )

            generate_otp(email)
            otp = cache.get(f"otp:{email}")
            send_otp(
                subject="OTP for email verification.",
                message=f'''Your otp for email vaification is {otp}. Enter this otp in otp verification section and hit varify to move forward.''',
                email=email
            )
            logger.info(f"OTP sent to email: {email}")
            return Response(
                    {
                        "status": True,
                        "message": "OTP sent.",
                        "data": {}
                    }
                )
        except Exception as e:
            logger.error(f"Exception in verifyEmail GET: {e}", exc_info=True)
            return Response(
                {
                    "status": False,
                    "message": "something went wrong.",
                    "data": {}
                }
            )

    def post(self, request):
        try:
            email = request.data.get("email")
            otp = request.data.get("otp")
            if varify_otp(email=email, otp=otp):
                cache.set(f"varified:{email}", True, 60*12)
                return Response(
                    {
                        "status": True,
                        "message": "OTP varified.",
                        "data": {}
                    }
                )
            else:
                return Response(
                    {
                        "status": False,
                        "message": "incorrect or invalid otp.",
                        "data": {}
                    }
                )
        except Exception as e:
            logger.error(f"Exception in verifyEmail GET: {e}", exc_info=True)
            return Response(
                {
                    "status": False,
                    "message": "something went wrong",
                    "data": {}
                }
            )


class ChangePassword(APIView):
    def post(self, request):
        try:
            data = request.data
            email = data.get("email")
            if cache.get(f"varified:{email}"):
                user = User.objects.get(email=email)
                new_password = data.get("new_password")
                if new_password:
                    if validate_new_passsword(new_password):
                        user.set_password(new_password)
                        user.save()
                        return Response(
                            {
                                "status": True,
                                "message": "password changed successfully.",
                                "data": {}
                            }
                        )
                    return Response(
                        {
                            "status": False,
                            "message": "Password must be at least 8 characters long and include an uppercase letter, a lowercase letter, a number, and a special character.",
                            "data": {}
                        }
                    )
                return Response(
                        {
                            "status": False,
                            "message": "New password not recived.",
                            "data": {}
                        }
                    )

            return Response(
                {
                    "status": False,
                    "message": "You are not authorized to perform this action.",
                    "data": {}
                }
            )

        except Exception as e:
            logger.error(f"Exception in verifyEmail GET: {e}", exc_info=True)
            return Response(
                {
                    "status": False,
                    "message": "something went wrong.",
                    "data": {}
                }
            )
