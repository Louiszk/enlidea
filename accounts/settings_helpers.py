from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta

MAX_ATTEMPTS = 5
LOCKOUT_DURATION = timedelta(hours=12)


def check_password_attempts(user):
    cache_key = f"password_attempts_{user.id}"
    attempts = cache.get(cache_key, 0)

    if attempts >= MAX_ATTEMPTS:
        lockout_time = cache.get(f"lockout_time_{user.id}")
        if lockout_time and timezone.now() < lockout_time:
            return False
        else:
            cache.delete(cache_key)
            cache.delete(f"lockout_time_{user.id}")
            return True

    return True


def increment_password_attempts(user):
    cache_key = f"password_attempts_{user.id}"

    try:
        attempts = cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, timeout=LOCKOUT_DURATION.total_seconds())
        attempts = 1

    if attempts >= MAX_ATTEMPTS:
        lockout_time = timezone.now() + LOCKOUT_DURATION
        cache.set(f"lockout_time_{user.id}", lockout_time, timeout=LOCKOUT_DURATION.total_seconds())
    return MAX_ATTEMPTS - attempts


def reset_password_attempts(user):
    cache_key = f"password_attempts_{user.id}"
    cache.delete(cache_key)
    cache.delete(f"lockout_time_{user.id}")


UPDATE_INTERVAL = timedelta(hours=8)


def can_update_personal_information(user):
    last_update_time = cache.get(f"last_update_time_{user.id}")
    if last_update_time and timezone.now() < last_update_time + UPDATE_INTERVAL:
        return False
    return True


def update_last_successful_update_time(user):
    cache.set(f"last_update_time_{user.id}", timezone.now())


def can_update_profile(user):
    last_update_time = cache.get(f"last_profile_update_time_{user.id}")
    if last_update_time and timezone.now() < last_update_time + UPDATE_INTERVAL:
        return False
    return True


def set_last_profile_update(user):
    cache.set(f"last_profile_update_time_{user.id}", timezone.now())
