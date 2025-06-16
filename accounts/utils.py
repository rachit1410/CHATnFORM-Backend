import random
from django.core.cache import cache
from accounts.models import VerifiedEmail
from django.core.mail import send_mail
from django.conf import settings
import re


def generate_otp(email) -> None:
    blocked = f"blocked:{email}"
    otp_cache = f"otp:{email}"
    otp = str(random.randint(100000, 999999))
    expiry_blocklist = 60*60*12
    expiry_otp = 60*12
    tries = 0

    if tries := cache.get(f"blocked:{email}"):
        tries = tries

    tries += 1
    cache.set(blocked, tries, expiry_blocklist)
    cache.set(otp_cache, otp, expiry_otp)


def varify_otp(email, otp):
    otp_cached = cache.get(f"otp:{email}")
    return otp_cached == str(otp)


def is_verified(email):
    VEmail, _ = VerifiedEmail.objects.get_or_create(email=email)
    return VEmail.verified


def send_otp(subject, message, email):
    send_mail(
        subject=subject,
        message=message,
        from_email=settings.FROM_EMAIL,
        recipient_list=[email],
        fail_silently=False,
    )


def validate_new_passsword(password):
    password_regex = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&#])[A-Za-z\d@$!%*?&#]{8,}$'
    return re.match(password_regex, password)
