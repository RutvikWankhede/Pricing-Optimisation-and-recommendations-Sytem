import os
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from starlette.middleware.base import BaseHTTPMiddleware
import logging
import sys
import uuid
from loguru import logger as loguru_logger
import sentry_sdk


from slowapi import Limiter
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.core.config import settings
from app.database.db import engine, Base
from app.api.routes import auth, upload, dashboard, forecasting, pricing, reports, health

# 1. Initialize Database Tables (auto-migration for development SQLite/PG)
Base.metadata.create_all(bind=engine)
try:
    from sqlalchemy import text
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE datasets ADD COLUMN summary_metadata TEXT"))
except Exception:
    pass

# 2. Initialize FastAPI App with rate limiting
limiter = Limiter(key_func=get_remote_address, default_limits=["100/minute"])  # 100 requests per minute per IP
app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Automated ML Pricing Elasticity, Demand Forecasting & Scenario Optimization.",
    version="1.0.0",
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, lambda request, exc: app.state.limiter._rate_limit_exceeded_handler(request, exc))
app.add_middleware(SlowAPIMiddleware)

# 3. Security Headers Middleware
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline';"
        # Remove potentially revealing header
        response.headers.pop("X-Powered-By", None)
        return response

app.add_middleware(SecurityHeadersMiddleware)
# Initialize Sentry
if settings.SENTRY_DSN:
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        traces_sample_rate=0.1,
        environment=os.getenv("ENVIRONMENT", "production")
    )
else:
    loguru_logger.warning("SENTRY_DSN not set; Sentry not initialized")

# Configure Loguru JSON logger
loguru_logger.remove()
loguru_logger.add(
    sys.stdout,
    format="{\"timestamp\":\"{time:YYYY-MM-DDTHH:mm:ssZ}\",\"level\":\"{level}\",\"message\":\"{message}\"}",
    level="INFO",
    serialize=True,
)

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
        logger = loguru_logger.bind(
            request_id=getattr(request.state, "request_id", None),
            path=request.url.path,
            method=request.method,
            user_id=getattr(request.state, "user_id", None)
        )
        logger.info("Incoming request")
        response = await call_next(request)
        logger.info(f"Response status: {response.status_code}")
        return response

app.add_middleware(LoggingMiddleware)
# 4. Configure CORS Middleware (read allowed origins from env, fallback to empty list for production)
allowed_origins = []
origins_env = os.getenv("CORS_ORIGINS")
if origins_env:
    allowed_origins = [origin.strip() for origin in origins_env.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
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
app.mount("/", StaticFiles(directory=settings.BASE_DIR / "frontend", html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
