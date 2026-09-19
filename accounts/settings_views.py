import logging
from typing import Any, cast

from decouple import config
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.db import IntegrityError, transaction
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.decorators import api_view, authentication_classes, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from main_api.services import cleanup_agent_active_node_commitments

from .serializers import PersonalInformationSerializer, ProfileSerializer
from .settings_helpers import (
    can_update_personal_information,
    can_update_profile,
    check_password_attempts,
    increment_password_attempts,
    reset_password_attempts,
    set_last_profile_update,
    update_last_successful_update_time,
)
from .tasks import send_async_verification_email

logger = logging.getLogger(__name__)


def sign_email(email):
    return signing.dumps(email, salt=str(config("SIGNING_KEY")))


def unsign_email(signed_email):
    try:
        email = signing.loads(signed_email, salt=str(config("SIGNING_KEY")), max_age=86400)
        return email
    except signing.BadSignature:
        return None


def send_verification_email(request, account, new_email):
    uidb64 = urlsafe_base64_encode(force_bytes(account.pk))
    token = default_token_generator.make_token(account)
    signed_email = sign_email(new_email)
    verification_link = f"{settings.FRONTEND_URL}/verify-email/{uidb64}/{token}/{signed_email}"

    transaction.on_commit(
        lambda: cast(Any, send_async_verification_email).delay(account.id, new_email, verification_link)
    )
    return True


@extend_schema(
    request=PersonalInformationSerializer,
    responses={
        200: inline_serializer(
            name="PersonalInformationResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
        400: inline_serializer(
            name="PersonalInformationErrorResponse",
            fields={
                "error": serializers.DictField(child=serializers.ListField(child=serializers.CharField())),
            },
        ),
        403: inline_serializer(
            name="PersonalInformationForbiddenResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
    },
)
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def personal_information(request):
    user = request.user

    if not can_update_personal_information(user):
        return Response(
            {"error": "You can only update personal information once every 8 hours."}, status=status.HTTP_403_FORBIDDEN
        )
    if not check_password_attempts(user):
        return Response(
            {"error": "Too many failed attempts. Updating personal information locked for 12 hours."},
            status=status.HTTP_403_FORBIDDEN,
        )

    serializer = PersonalInformationSerializer(user, data=request.data, partial=True, context={"request": request})

    if not serializer.is_valid():
        return Response({"error": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    current_password = serializer.validated_data.get("current_password")

    if not authenticate(username=user.email, password=current_password):
        attempts = increment_password_attempts(user)
        if attempts <= 3:
            return Response(
                {
                    "error": f"Current password is incorrect. You have {attempts} attempt{'s' if attempts > 1 else ''} left."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )
        else:
            return Response({"error": "Current password is incorrect."}, status=status.HTTP_400_BAD_REQUEST)

    reset_password_attempts(user)
    update_last_successful_update_time(user)

    new_email = serializer.validated_data.get("email")
    with transaction.atomic():
        if new_email and new_email != user.email:
            serializer.save()
            send_verification_email(request, user, new_email)
            return Response(
                {
                    "message": "We have sent you a validation link at your new email. If you cannot verify your email, it will stay as before."
                },
                status=status.HTTP_200_OK,
            )
        serializer.save()

    return Response({"message": "Personal information updated successfully."}, status=status.HTTP_200_OK)


@extend_schema(
    responses={
        200: inline_serializer(
            name="VerifyEmailResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
        400: inline_serializer(
            name="VerifyEmailErrorResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
    }
)
@api_view(["GET"])
@authentication_classes([])
@permission_classes([AllowAny])
def verify_email(request, uidb64, token, signed_email):
    User = get_user_model()
    new_email = None
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        user = User.objects.get(pk=uid)
        new_email = unsign_email(signed_email)
        if new_email is None:
            return Response(
                {"error": "Invalid or expired email verification link."}, status=status.HTTP_400_BAD_REQUEST
            )
    except (TypeError, ValueError, OverflowError, User.DoesNotExist):
        user = None

    if user is not None and new_email is not None and default_token_generator.check_token(user, token):
        # Verify that the new email is not already in use
        if User.objects.filter(email__iexact=new_email).exclude(pk=user.pk).exists():
            return Response({"error": "This email is already in use."}, status=status.HTTP_400_BAD_REQUEST)

        # Update the user's email
        try:
            user.email = new_email
            user.save(update_fields=["email"])
            return Response({"message": "Email successfully verified and updated."}, status=status.HTTP_200_OK)
        except IntegrityError:
            return Response({"error": "This email is already in use."}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return Response({"error": "Invalid verification link."}, status=status.HTTP_400_BAD_REQUEST)


@extend_schema(
    request=inline_serializer(
        name="DeleteAccountRequest",
        fields={
            "password": serializers.CharField(),
        },
    ),
    responses={
        200: inline_serializer(
            name="DeleteAccountResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
        400: inline_serializer(
            name="DeleteAccountErrorResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
        500: inline_serializer(
            name="DeleteAccountInternalErrorResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
    },
)
@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_account(request):
    password = request.data.get("password")
    user = request.user

    # Authenticate the user
    if not authenticate(username=user.email, password=password):
        return Response({"error": "Invalid password"}, status=status.HTTP_400_BAD_REQUEST)

    try:
        with transaction.atomic():
            for agent in user.agents.all():
                cleanup_agent_active_node_commitments(agent)
            user.delete()
        return Response({"message": "Account deleted successfully"}, status=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error deleting account: {e!s}")
        return Response(
            {"error": "Failed to delete account due to an internal error."},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@extend_schema(
    request=ProfileSerializer,
    responses={
        200: inline_serializer(
            name="UpdateProfileResponse",
            fields={
                "message": serializers.CharField(),
            },
        ),
        403: inline_serializer(
            name="UpdateProfileForbiddenResponse",
            fields={
                "error": serializers.CharField(),
            },
        ),
    },
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    user = request.user
    if not can_update_profile(user):
        return Response(
            {"error": "You can only update your profile once every 8 hours."}, status=status.HTTP_403_FORBIDDEN
        )
    serializer = ProfileSerializer(instance=user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        set_last_profile_update(user)
        return Response({"message": "Profile updated successfully"}, status=status.HTTP_200_OK)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
