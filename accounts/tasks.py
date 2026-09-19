import logging

from celery import shared_task
from celery.exceptions import MaxRetriesExceededError, Retry
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_async_activation_email(self, user_id, activation_link):
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"Failed to send activation email: User {user_id} not found.")
        return

    try:
        mail_subject = "Activate your Enlidea account."
        message = render_to_string(
            "accounts/account_activation_email.html", {"account": user, "activation_link": activation_link}
        )
        send_mail(
            mail_subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        logger.info(f"Activation email sent to {user.email}")
    except (Retry, MaxRetriesExceededError):
        raise
    except Exception as e:
        logger.error(f"Error sending activation email to user {user_id}: {e!s}")
        if self.request.retries >= self.max_retries:
            logger.critical(
                f"METRIC email_delivery_failure task=send_async_activation_email user_id={user_id} error={e!s}"
            )
            raise MaxRetriesExceededError(f"Can't retry {self.name}: max retries exceeded") from e
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_async_password_reset_email(self, user_id, reset_link):
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"Failed to send password reset email: User {user_id} not found.")
        return

    try:
        mail_subject = "Reset your Enlidea account password."
        message = render_to_string("accounts/password_reset_email.html", {"account": user, "reset_link": reset_link})
        send_mail(
            mail_subject,
            message,
            settings.EMAIL_HOST_USER,
            [user.email],
            fail_silently=False,
        )
        logger.info(f"Password reset email sent to {user.email}")
    except (Retry, MaxRetriesExceededError):
        raise
    except Exception as e:
        logger.error(f"Error sending password reset email to user {user_id}: {e!s}")
        if self.request.retries >= self.max_retries:
            logger.critical(
                f"METRIC email_delivery_failure task=send_async_password_reset_email user_id={user_id} error={e!s}"
            )
            raise MaxRetriesExceededError(f"Can't retry {self.name}: max retries exceeded") from e
        raise self.retry(exc=e)


@shared_task(
    bind=True,
    max_retries=5,
    default_retry_delay=5,
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
)
def send_async_verification_email(self, user_id, new_email, verification_link):
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.error(f"Failed to send verification email: User {user_id} not found.")
        return

    try:
        mail_subject = "Change your Enlidea account email address."
        message = render_to_string(
            "accounts/account_change_email.html", {"account": user, "verification_link": verification_link}
        )
        send_mail(
            mail_subject,
            message,
            settings.EMAIL_HOST_USER,
            [new_email],
            fail_silently=False,
        )
        logger.info(f"Email change verification sent to {new_email}")
    except (Retry, MaxRetriesExceededError):
        raise
    except Exception as e:
        logger.error(f"Error sending verification email for user {user_id}: {e!s}")
        if self.request.retries >= self.max_retries:
            logger.critical(
                f"METRIC email_delivery_failure task=send_async_verification_email user_id={user_id} error={e!s}"
            )
            raise MaxRetriesExceededError(f"Can't retry {self.name}: max retries exceeded") from e
        raise self.retry(exc=e)
