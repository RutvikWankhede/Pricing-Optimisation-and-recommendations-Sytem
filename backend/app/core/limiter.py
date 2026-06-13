import os
from typing import Callable, Any

# Simple stub for rate limiting when slowapi is unavailable.
# In production you can replace this with the real SlowAPI Limiter.

class DummyLimiter:
    def limit(self, limit_str: str) -> Callable[[Any], Any]:
        def decorator(func: Any) -> Any:
            return func
        return decorator

# Attempt to import real Limiter; fallback to dummy.
try:
    from slowapi import Limiter as RealLimiter
    limiter = RealLimiter(key_func=lambda request: request.client.host, default_limits=["100/minute"])
except Exception:
    limiter = DummyLimiter()

# Export name expected by other modules.
__all__ = ["limiter"]
