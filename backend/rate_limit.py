"""Lightweight in-memory sliding-window rate limiter.

Protects brute-force-sensitive endpoints (auth) without external deps. Keys are
derived from the client IP (proxy-aware via X-Forwarded-For) and, for login,
also the target email so a distributed attack on one account is throttled.

Single-instance MVP scope: state is per-process (not shared across replicas).
"""
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

_hits: dict[str, deque] = defaultdict(deque)


def client_ip(request: Request) -> str:
    """Best-effort real client IP behind the Kubernetes ingress/proxy."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    real = request.headers.get("x-real-ip")
    if real:
        return real.strip()
    return request.client.host if request.client else "unknown"


def enforce(key: str, max_hits: int, window_seconds: int) -> None:
    """Record a hit for `key`; raise HTTP 429 if it exceeds max_hits/window."""
    now = time.time()
    dq = _hits[key]
    cutoff = now - window_seconds
    while dq and dq[0] < cutoff:
        dq.popleft()
    if len(dq) >= max_hits:
        retry_after = int(dq[0] + window_seconds - now) + 1
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many attempts. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )
    dq.append(now)


def reset(key: str) -> None:
    """Clear a bucket (e.g. after a successful login) so legit users aren't locked."""
    _hits.pop(key, None)
