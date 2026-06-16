import logging
from django.conf import settings

logger = logging.getLogger(__name__)

from main_api.tasks import send_async_activation_email, send_async_password_reset_email
from django.core.cache import cache
from typing import Any, cast
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, authentication_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import get_user_model, authenticate
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.core.exceptions import ValidationError
from .serializers import AccountSerializer, EmailSerializer, PasswordResetConfirmSerializer, PasswordSerializer
from .models import validate_username
from .authentication import CookieJWTAuthentication
from .throttling import UsernameCheckThrottle
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from django.db import transaction, IntegrityError
from .auth_helpers import check_login_attempts, increment_login_attempts, reset_login_attempts, get_remaining_attempts
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from rest_framework import serializers


# VERIFICATION EMAIL
def can_send_verification_email(user_id):
    cache_key = f"last_verification_email_{user_id}"
    last_sent = cache.get(cache_key)
    if last_sent is None:
        return True
    return (timezone.now() - last_sent).total_seconds() > 600


def set_verification_email_sent(user_id):
    cache_key = f"last_verification_email_{user_id}"
    cache.set(cache_key, timezone.now(), timeout=600)


def send_activation_email(request, account):
    uidb64 = urlsafe_base64_encode(force_bytes(account.pk))
    token = default_token_generator.make_token(account)
    activation_link = f"{settings.FRONTEND_URL}/activate/{uidb64}/{token}"

    cast(Any, send_async_activation_email).delay(account.id, activation_link)
    return True


# PASSWORT RESET EMAIL
def send_password_reset_email(request, account):
    uidb64 = urlsafe_base64_encode(force_bytes(account.pk))
    token = default_token_generator.make_token(account)
    reset_link = f"{settings.FRONTEND_URL}/password-reset-confirm/{uidb64}/{token}"

    cast(Any, send_async_password_reset_email).delay(account.id, reset_link)
    return True


def can_send_password_reset_email(user_id):
    cache_key = f"last_password_reset_email_{user_id}"
    last_sent = cache.get(cache_key)
    if last_sent is None:
        return True
    return (timezone.now() - last_sent).total_seconds() > 600


def set_password_reset_email_sent(user_id):
    cache_key = f"last_password_reset_email_{user_id}"
    cache.set(cache_key, timezone.now(), timeout=600)


# API FUNCTIONS


@extend_schema(
    parameters=[
        OpenApiParameter(
            name="username",
            description="Username to check",
            required=True,
            type=str,
        )
    ],
    responses={
        200: inline_serializer(
            name="CheckUsernameResponse",
            fields={
                "is_valid": serializers.BooleanField(),
                "is_taken": serializers.BooleanField(),
                "message": serializers.CharField(),
            },
        ),
        400: inline_serializer(
            name="CheckUsernameBadRequestResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
    },
)
@api_view(["GET"])
@permission_classes([AllowAny])
@throttle_classes([UsernameCheckThrottle])
def check_username(request):
    username = request.query_params.get("username")
    if not username:
        return Response({"error": "Username is required"}, status=status.HTTP_400_BAD_REQUEST)

    # 1. Check Format/Regex
    try:
        validate_username(username)
    except ValidationError as e:
        return Response({"is_valid": False, "is_taken": False, "message": e.message})

    # 2. Check Availability
    is_taken = get_user_model().objects.filter(username__iexact=username).exists()
    return Response(
        {
            "is_valid": True,
            "is_taken": is_taken,
            "message": "Username is already taken" if is_taken else "Username is available",
        }
    )


@extend_schema(
    request=inline_serializer(
        name="RegisterRequest",
        fields={
            "email": serializers.EmailField(),
            "username": serializers.CharField(),
            "password1": serializers.CharField(),
            "password2": serializers.CharField(),
        },
    ),
    responses={
        201: inline_serializer(
            name="RegisterResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    password_serializer = PasswordSerializer(data=request.data)
    if not password_serializer.is_valid():
        return Response(password_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    # Create a new dict with the validated data
    account_data = {
        "email": request.data.get("email"),
        "username": request.data.get("username"),
        "password": password_serializer.validated_data["password1"],
    }

    serializer = AccountSerializer(data=account_data)
    if serializer.is_valid():
        user = serializer.save(is_active=False)
        if send_activation_email(request, user):
            return Response(
                {"message": "User registered successfully. Please check your email for the activation link."},
                status=status.HTTP_201_CREATED,
            )
        else:
            user.delete()
            return Response({"error": "Failed to send activation email."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    responses={
        200: inline_serializer(
            name="ActivateAccountResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
        400: inline_serializer(
            name="ActivateAccountErrorResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
    }
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def activate_account(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = get_user_model()._default_manager.get(pk=uid)
    except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
        user = None
    if user is not None:
        if user.is_active:
            return Response({"message": "Account is already activated."}, status=status.HTTP_200_OK)
        if default_token_generator.check_token(user, token):
            with transaction.atomic():
                user.is_active = True

                # Tokenomics: Closed-loop signup bonus (if Treasury allows)
                from main_api.tasks import TREASURY_USERNAME
                from decimal import Decimal

                try:
                    treasury_acc = get_user_model().objects.select_for_update().get(username=TREASURY_USERNAME)
                    signup_bonus = Decimal("100.0000")

                    if treasury_acc.balance_blue_stars >= signup_bonus:
                        treasury_acc.balance_blue_stars -= signup_bonus
                        treasury_acc.save(update_fields=["balance_blue_stars"])
                        user.balance_blue_stars = signup_bonus
                    else:
                        user.balance_blue_stars = Decimal("0.0000")
                except get_user_model().DoesNotExist:
                    user.balance_blue_stars = Decimal("0.0000")

                user.save(update_fields=["is_active", "balance_blue_stars"])
            return Response({"message": "Account activated successfully."}, status=status.HTTP_200_OK)
        else:
            return Response(
                {"error": "Invalid activation link. Maybe it expired? Go to the Login-Page to request a new one."},
                status=status.HTTP_400_BAD_REQUEST,
            )
    else:
        return Response({"error": "Invalid activation link."}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=inline_serializer(
        name="LoginRequest",
        fields={
            "email": serializers.EmailField(),
            "password": serializers.CharField(),
        },
    ),
    responses={
        200: inline_serializer(
            name="LoginResponse",
            fields={
                "message": serializers.CharField(),
                "user": AccountSerializer(),
            },
        ),
        400: inline_serializer(
            name="LoginErrorResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
        403: inline_serializer(
            name="LoginForbiddenResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
        429: inline_serializer(
            name="LoginRateLimitResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def login_view(request):
    if not check_login_attempts(request):
        return Response(
            {"error": "Too many failed login attempts. Please try again 12 hours."},
            status=status.HTTP_429_TOO_MANY_REQUESTS,
        )

    email = request.data.get("email")
    password = request.data.get("password")
    user = authenticate(username=email, password=password)

    if user:
        if user.is_active:
            reset_login_attempts(request)
            refresh = RefreshToken.for_user(user)

            response = Response(
                {"message": "Login successful.", "user": AccountSerializer(user).data}, status=status.HTTP_200_OK
            )

            response.set_cookie(
                "access", str(refresh.access_token), httponly=True, samesite="Lax", secure=not settings.DEBUG, path="/"
            )
            response.set_cookie(
                "refresh", str(refresh), httponly=True, samesite="Lax", secure=not settings.DEBUG, path="/"
            )
            return response
        else:
            return Response({"error": "Your email has not been verified."}, status=status.HTTP_403_FORBIDDEN)
    else:
        increment_login_attempts(request)
        remaining_attempts = get_remaining_attempts(request)
        if remaining_attempts > 0:
            if remaining_attempts > 3:
                return Response({"error": "Invalid login."}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response(
                    {
                        "error": f"Invalid login. You have {remaining_attempts} attempt{'s' if remaining_attempts > 1 else ''} remaining."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )
        else:
            return Response(
                {"error": "Too many failed login attempts. Please try again in 12 hours."},
                status=status.HTTP_429_TOO_MANY_REQUESTS,
            )


@extend_schema(
    request=EmailSerializer,
    responses={
        200: inline_serializer(
            name="ResendActivationResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
        404: inline_serializer(
            name="ResendActivationNotFoundResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
        429: inline_serializer(
            name="ResendActivationRateLimitResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def resend_activation(request):
    serializer = EmailSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data["email"]
        User = get_user_model()
        try:
            user = User.objects.get(email=email, is_active=False)
            if can_send_verification_email(user.id):
                if send_activation_email(request, user):
                    set_verification_email_sent(user.id)
                    return Response({"message": "Activation email sent successfully."}, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {"error": "Failed to send activation email."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            else:
                return Response(
                    {"error": "Please wait at least 10 minutes before requesting another activation email."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )
        except User.DoesNotExist:
            return Response(
                {"error": "No inactive account found with this email address."}, status=status.HTTP_404_NOT_FOUND
            )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=EmailSerializer,
    responses={
        200: inline_serializer(
            name="PasswordResetResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset(request):
    serializer = EmailSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data["email"]
        User = get_user_model()
        try:
            user = User.objects.get(email=email)

            if can_send_password_reset_email(user.id):
                if send_password_reset_email(request, user):
                    set_password_reset_email_sent(user.id)
                    return Response({"message": "Password reset email sent successfully."}, status=status.HTTP_200_OK)
                else:
                    return Response(
                        {"error": "An unexpected error occurred. Please try again later."},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    )
            else:
                return Response(
                    {"error": "Please wait 10 minutes before requesting another password reset."},
                    status=status.HTTP_429_TOO_MANY_REQUESTS,
                )

        except User.DoesNotExist:
            pass
        # To prevent user enumeration, we'll show the same message as if the email was sent
        return Response(
            {"message": "If an account exists with this email, a password reset link has been sent."},
            status=status.HTTP_200_OK,
        )
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=inline_serializer(
        name="PasswordResetConfirmRequest",
        fields={
            "new_password1": serializers.CharField(),
            "new_password2": serializers.CharField(),
        },
    ),
    responses={
        200: inline_serializer(
            name="PasswordResetConfirmResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request, uidb64, token):
    data = {
        "uid": uidb64,
        "token": token,
        "new_password1": request.data.get("new_password1"),
        "new_password2": request.data.get("new_password2"),
    }
    serializer = PasswordResetConfirmSerializer(data=data)
    if serializer.is_valid():
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = get_user_model()._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if default_token_generator.check_token(user, token):
            user.set_password(serializer.validated_data["new_password1"])
            user.save()
            return Response({"message": "Password has been reset successfully."}, status=status.HTTP_200_OK)
        else:
            return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=None,
    responses={
        200: inline_serializer(
            name="LogoutResponse",
            fields={
                "message": serializers.CharField(),
            },
        )
    },
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def logout_view(request):
    refresh_token = request.COOKIES.get("refresh")

    if refresh_token:
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except (TokenError, IntegrityError):
            # Token is already invalid, blacklisted, or DB constraint already met
            pass

    response = Response({"message": "Logged out securely"}, status=status.HTTP_200_OK)
    response.delete_cookie("access", path="/")
    response.delete_cookie("refresh", path="/")
    return response


from django.views.decorators.csrf import ensure_csrf_cookie


@extend_schema(
    request=None,
    responses={
        200: AccountSerializer,
        401: inline_serializer(
            name="CurrentUserUnauthorizedResponse",
            fields={
                "detail": serializers.CharField(),
            },
        ),
    },
)
@api_view(["GET"])
@authentication_classes([CookieJWTAuthentication])
@permission_classes([AllowAny])
@ensure_csrf_cookie
def current_user(request):
    if not request.user or not request.user.is_authenticated:
        return Response({"detail": "Not logged in"}, status=status.HTTP_401_UNAUTHORIZED)
    serializer = AccountSerializer(request.user)
    return Response(serializer.data)


@extend_schema(
    request=None,
    responses={
        200: inline_serializer(
            name="TokenRefreshResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
        400: inline_serializer(
            name="TokenRefreshErrorResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
        401: inline_serializer(
            name="TokenRefreshUnauthorizedResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@authentication_classes([])
@permission_classes([AllowAny])
def token_refresh(request):
    refresh_token = request.COOKIES.get("refresh")
    if not refresh_token:
        return Response({"error": "No refresh token provided"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)

        # Rotate the refresh token
        refresh.set_jti()
        refresh.set_exp()

        response = Response({"message": "Token refreshed successfully"})

        response.set_cookie("access", access_token, httponly=True, samesite="Lax", secure=not settings.DEBUG, path="/")
        response.set_cookie("refresh", str(refresh), httponly=True, samesite="Lax", secure=not settings.DEBUG, path="/")
        return response
    except TokenError:
        # If refresh fails, clear cookies to prevent further attempts
        response = Response({"error": "Invalid refresh token"}, status=status.HTTP_401_UNAUTHORIZED)
        response.delete_cookie("access", path="/")
        response.delete_cookie("refresh", path="/")
        return response
