from django.core.cache import cache
from django.conf import settings

MAX_LOGIN_ATTEMPTS = getattr(settings, 'MAX_LOGIN_ATTEMPTS', 5)
LOGIN_ATTEMPT_TIMEOUT = getattr(settings, 'LOGIN_ATTEMPT_TIMEOUT', 43200) 

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        # Nginx appends the real client IP to the END of the list
        ip = x_forwarded_for.split(',')[-1].strip()
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip

def check_login_attempts(request):
    client_ip = get_client_ip(request)
    cache_key = f"login_attempts_{client_ip}"
    login_attempts = cache.get(cache_key, 0)
    
    if login_attempts >= MAX_LOGIN_ATTEMPTS:
        return False
    return True

def increment_login_attempts(request):
    client_ip = get_client_ip(request)
    cache_key = f"login_attempts_{client_ip}"
    
    # Atomically increment, or set to 1 if it doesn't exist
    try:
        cache.incr(cache_key)
    except ValueError:
        cache.set(cache_key, 1, LOGIN_ATTEMPT_TIMEOUT)

def reset_login_attempts(request):
    client_ip = get_client_ip(request)
    cache_key = f"login_attempts_{client_ip}"
    cache.delete(cache_key)

def get_remaining_attempts(request):
    client_ip = get_client_ip(request)
    cache_key = f"login_attempts_{client_ip}"
    login_attempts = cache.get(cache_key, 0)
    return max(0, MAX_LOGIN_ATTEMPTS - login_attempts)
