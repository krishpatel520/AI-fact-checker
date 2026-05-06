"""
rate_limit.py
-------------
Per-IP rate limiting using slowapi (Starlette-native Limiter backed by Redis).

Limits
------
  /api/verify/*   — 10 requests / minute per IP  (expensive pipeline)
  /api/result/*   — 60 requests / minute per IP  (cheap poll endpoint)
  /api/job/*      — 60 requests / minute per IP
  /api/recent     — 30 requests / minute per IP

Usage in main.py
----------------
  from backend.middleware.rate_limit import limiter, rate_limit_handler
  app.state.limiter = limiter
  app.add_exception_handler(RateLimitExceeded, rate_limit_handler)

  @app.post("/api/verify/url")
  @limiter.limit("10/minute")
  async def verify_url(request: Request, ...):
      ...
"""

import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=REDIS_URL,
    default_limits=["200/minute"],
)

rate_limit_handler = _rate_limit_exceeded_handler

__all__ = ["limiter", "rate_limit_handler", "RateLimitExceeded"]
