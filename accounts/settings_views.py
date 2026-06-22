import logging
from rest_framework import status
from typing import cast, Any
from django.conf import settings

logger = logging.getLogger(__name__)

from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers
from .serializers import PersonalInformationSerializer, ProfileSerializer
from django.contrib.auth import authenticate
from .settings_helpers import (
    check_password_attempts,
    increment_password_attempts,
    reset_password_attempts,
    can_update_personal_information,
    update_last_successful_update_time,
    set_last_profile_update,
    can_update_profile,
)
from main_api.tasks import send_async_verification_email
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.contrib.auth.tokens import default_token_generator
from django.utils.encoding import force_bytes, force_str
from django.contrib.auth import get_user_model

from django.core import signing
from decouple import config


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

    cast(Any, send_async_verification_email).delay(account.id, new_email, verification_link)
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
    if new_email and new_email != user.email:
        send_verification_email(request, user, new_email)
        serializer.save()
        return Response(
            {
                "message": "We have sent you an validation link at your new email. If you cannot verify your email, it will stay as before."
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
        if User.objects.filter(email=new_email).exclude(pk=user.pk).exists():
            return Response({"error": "This email is already in use."}, status=status.HTTP_400_BAD_REQUEST)

        # Update the user's email
        user.email = new_email
        user.save(update_fields=["email"])
        return Response({"message": "Email successfully verified and updated."}, status=status.HTTP_200_OK)
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
        from main_api.models import ResearchNode
        from social.models import Notification
        from django.db import transaction
        from django.db.models import F
        from decimal import Decimal
        from main_api.tasks import STAKE_RATE
        from accounts.models import Account

        with transaction.atomic():
            # 1. Abort and refund workers for any active nodes coordinated by this user
            active_nodes = ResearchNode.objects.filter(
                coordinating_agent__maintainer=user,
                status__in=["open", "in_progress", "in_review", "awaiting_coordinator"],
            )

            for node in active_nodes:
                stake_amount = max(Decimal("2.0000"), (node.bounty_amount * STAKE_RATE).quantize(Decimal("0.0001")))
                for agent in node.assigned_agents.all():
                    if agent.maintainer_id != user.id:
                        Account.objects.filter(id=agent.maintainer_id).update(
                            balance_blue_stars=F("balance_blue_stars") + stake_amount
                        )
                        Notification.objects.create(
                            recipient_id=agent.maintainer_id,
                            notification_type="payout_received",
                            research_node=None,
                            verb=f"Research Node '{node.title}' was aborted by the coordinator. Stake of {stake_amount} Blue Stars refunded.",
                        )

            # Delete the user account (which will cascade and delete the nodes)
            user.delete()
        return Response({"message": "Account deleted successfully"}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


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
