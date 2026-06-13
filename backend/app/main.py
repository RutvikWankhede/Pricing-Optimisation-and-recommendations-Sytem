import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import sys
import uuid

# Logging will be configured later

try:
    import sentry_sdk
except ImportError:
    sentry_sdk = None

# SlowAPI is optional; we rely on our internal limiter fallback.
# Importing SlowAPI is avoided to prevent startup errors when the package is missing.
SLOWAPI_AVAILABLE = False

from app.core.config import settings
from app.database.db import engine, Base
from app.api.routes import (
    auth,
    upload,
    dashboard,
    forecasting,
    pricing,
    reports,
    health,
)

# 1. Initialize Database Tables (auto-migration for development SQLite/PG)
Base.metadata.create_all(bind=engine)
try:
    from sqlalchemy import text

    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE datasets ADD COLUMN summary_metadata TEXT"))
except Exception:
    pass

# 2. Initialize FastAPI App with rate limiting
from app.core.limiter import limiter

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Automated ML Pricing Elasticity, Demand Forecasting & Scenario Optimization.",
    version="1.0.0",
)

# Set limiter in app state
app.state.limiter = limiter
# Register SlowAPI middleware and exception handler when the real limiter is available.
try:
    from slowapi import _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    app.add_middleware(SlowAPIMiddleware)
except ImportError:
    pass  # slowapi not installed; DummyLimiter is in use — no middleware needed.


# 3. Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "font-src 'self' data: https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "connect-src 'self' https://cdn.tailwindcss.com https://cdn.jsdelivr.net;"
        )
        # Remove potentially revealing header
        if "X-Powered-By" in response.headers:
            del response.headers["X-Powered-By"]
        return response


app.add_middleware(SecurityHeadersMiddleware)
# Initialize Sentry
if settings.SENTRY_DSN and sentry_sdk:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "production"),
    )
else:
    logging.getLogger("uvicorn").warning(
        "Sentry not initialized (SDK missing or DSN not set)"
    )

# Configure standard logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("uvicorn")


# Request ID Middleware
class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response


app.add_middleware(RequestIDMiddleware)


# Logging Middleware
class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        logger = logging.getLogger("uvicorn")
        logger.info(
            f"Incoming request {request.method} {request.url.path} request_id={getattr(request.state, 'request_id', None)}"
        )
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response


app.add_middleware(LoggingMiddleware)
# 4. Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5500",
        "http://127.0.0.1:5500",
        "http://localhost:3000",
        "https://pricing-optimisation-and-recommenda.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 5. Include Versioned API Routes
api_prefix = "/api/v1"
app.include_router(auth.router, prefix=api_prefix)
app.include_router(upload.router, prefix=api_prefix)
app.include_router(dashboard.router, prefix=api_prefix)
app.include_router(forecasting.router, prefix=api_prefix)
app.include_router(pricing.router, prefix=api_prefix)
app.include_router(reports.router, prefix=api_prefix)
app.include_router(health.router)

# 6. Serve Static Frontend Files
app.mount(
    "/",
    StaticFiles(directory=settings.BASE_DIR / "frontend", html=True),
    name="frontend",
)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
