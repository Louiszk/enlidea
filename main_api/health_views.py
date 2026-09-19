import logging

from django.core.cache import cache
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    authentication_classes,
    permission_classes,
    throttle_classes,
)
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

logger = logging.getLogger(__name__)


@extend_schema(exclude=True)
@api_view(["GET"])
@permission_classes([AllowAny])
@authentication_classes([])
@throttle_classes([])
def healthz_view(request):
    """
    Lightweight process liveness probe. Returns 200 OK without dependency checks.
    """
    return Response({"status": "healthy"}, status=status.HTTP_200_OK)


@extend_schema(exclude=True)
@api_view(["GET"])
@permission_classes([AllowAny])
@authentication_classes([])
@throttle_classes([])
def readyz_view(request):
    """
    Readiness probe for orchestrators and reverse proxies.
    Checks PostgreSQL and Redis connectivity with short timeouts, sanitizing internal error details.
    """
    db_ok = False
    cache_ok = False

    try:
        connection.ensure_connection()
        db_ok = connection.is_usable()
    except Exception as e:
        logger.warning(f"Readiness probe DB failure: {e}")
        db_ok = False

    try:
        # Perform a lightweight read check without churning keys in Redis
        cache.get("readiness_probe")
        cache_ok = True
    except Exception as e:
        logger.warning(f"Readiness probe Cache failure: {e}")
        cache_ok = False

    data = {
        "status": "ready" if (db_ok and cache_ok) else "degraded",
        "database": "ok" if db_ok else "unreachable",
        "cache": "ok" if cache_ok else "unreachable",
    }

    if db_ok and cache_ok:
        return Response(data, status=status.HTTP_200_OK)
    return Response(data, status=status.HTTP_503_SERVICE_UNAVAILABLE)
