from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import Depends, FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi_csrf_protect import CsrfProtect
from fastapi_csrf_protect.exceptions import CsrfProtectError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.v1 import (
    ai_tasks,
    analytics,
    auth,
    beauty,
    booth_health,
    booths,
    camera,
    disclaimers,
    events,
    gopro,
    green_screen,
    media,
    photos,
    print_jobs,
    printers,
    props,
    share_settings,
    shares,
    signatures,
    subscriptions,
    surveys,
    sync,
    teams,
    templates,
    triggers,
    virtual_attendant,
    watermark,
    webhooks,
)
from app.core.config import settings
from app.core.exceptions import (
    general_exception_handler,
    http_exception_handler,
    validation_exception_handler,
)
from app.core.logging import logger
from app.core.rate_limit import RateLimitMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown"""
    # Startup
    logger.info(f"Starting {settings.APP_NAME} v{settings.VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    if settings.SENTRY_DSN and settings.ENVIRONMENT != "development":
        import sentry_sdk
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.fastapi import FastApiIntegration

        sentry_sdk.init(
            dsn=settings.SENTRY_DSN,
            traces_sample_rate=1.0,
            integrations=[
                FastApiIntegration(transaction_style="endpoint"),
                CeleryIntegration(),
            ],
            environment=settings.ENVIRONMENT,
            release=settings.VERSION,
        )

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME}")


# CSRF Protection Configuration
@CsrfProtect.load_config
def get_csrf_config():
    return [
        ("secret_key", settings.CSRF_SECRET_KEY or settings.SECRET_KEY),
        ("cookie_secure", settings.CSRF_COOKIE_SECURE or settings.ENVIRONMENT == "production"),
        ("cookie_samesite", settings.CSRF_COOKIE_SAMESITE),
        ("cookie_key", "csrftoken"),
        ("header_name", "X-CSRF-Token"),
    ]


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
    debug=settings.DEBUG,
    description="AI Booth API - Photo booth management with AI-powered features",
    contact={
        "name": "AI Booth Support",
        "email": "support@aibooth.app",
    },
    license_info={
        "name": "Proprietary",
    },
    lifespan=lifespan,
)

# Exception handlers
app.add_exception_handler(StarletteHTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


@app.exception_handler(CsrfProtectError)
async def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    """Handle CSRF protection errors"""
    logger.warning(f"CSRF validation failed: {exc} from {request.client.host}")
    return JSONResponse(status_code=403, content={"detail": "CSRF token validation failed"})


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.CORS_CREDENTIALS,
    allow_methods=[m.strip() for m in settings.CORS_METHODS.split(",")],
    allow_headers=[h.strip() for h in settings.CORS_HEADERS.split(",")],
    expose_headers=["X-CSRF-Token"],  # Allow frontend to read CSRF token
)

# Rate limiting middleware
app.add_middleware(RateLimitMiddleware)


# Security headers middleware
@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["Permissions-Policy"] = settings.PERMISSIONS_POLICY
    response.headers["Content-Security-Policy"] = settings.CONTENT_SECURITY_POLICY
    return response


# Local uploaded media for development / single-node deployments.
Path("uploads").mkdir(exist_ok=True)

# Include routers
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Authentication"])
app.include_router(teams.router, prefix="/api/v1/teams", tags=["Teams"])
app.include_router(events.router, prefix="/api/v1/events", tags=["Events"])
app.include_router(photos.router, prefix="/api/v1/photos", tags=["Photos"])
app.include_router(templates.router, prefix="/api/v1/templates", tags=["Templates"])
app.include_router(print_jobs.router, prefix="/api/v1/print-jobs", tags=["Print Jobs"])
app.include_router(shares.router, prefix="/api/v1/shares", tags=["Shares"])
app.include_router(ai_tasks.router, prefix="/api/v1/ai-tasks", tags=["AI Tasks"])
app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
app.include_router(subscriptions.router, prefix="/api/v1/subscriptions", tags=["Subscriptions"])
app.include_router(media.router, prefix="/api/v1/media", tags=["Media"])
app.include_router(watermark.router, prefix="/api/v1", tags=["Watermark"])
app.include_router(beauty.router, prefix="/api/v1/beauty", tags=["Beauty"])
app.include_router(
    virtual_attendant.router, prefix="/api/v1/virtual-attendant", tags=["Virtual Attendant"]
)
app.include_router(signatures.router, prefix="/api/v1", tags=["Signatures"])
app.include_router(surveys.router, prefix="/api/v1", tags=["Surveys"])
app.include_router(disclaimers.router, prefix="/api/v1", tags=["Disclaimers"])
app.include_router(props.router, prefix="/api/v1/props", tags=["Props"])
app.include_router(share_settings.router, prefix="/api/v1", tags=["Share Settings"])
app.include_router(green_screen.router, prefix="/api/v1/green-screen", tags=["Green Screen"])
app.include_router(printers.router, prefix="/api/v1/printers", tags=["Printers"])
app.include_router(camera.router, prefix="/api/v1/camera", tags=["Camera"])
app.include_router(booths.router, prefix="/api/v1", tags=["Booths"])
app.include_router(sync.router, prefix="/api/v1", tags=["Sync"])
app.include_router(triggers.router, prefix="/api/v1/triggers", tags=["Triggers"])
app.include_router(gopro.router, prefix="/api/v1/gopro", tags=["GoPro"])
app.include_router(webhooks.router, prefix="/api/v1/webhooks", tags=["Webhooks"])
app.include_router(booth_health.router, prefix="/api/v1/booth", tags=["Booth Health"])


@app.get("/csrf-token")
async def get_csrf_token(csrf_protect: CsrfProtect = Depends()):
    """
    Get CSRF token for frontend
    Frontend should call this on app load and include token in POST/PUT/DELETE requests
    """
    csrf_token, signed_token = csrf_protect.generate_csrf_tokens()
    response = JSONResponse({"csrf_token": csrf_token})
    csrf_protect.set_csrf_cookie(signed_token, response)
    return response


@app.get("/")
async def root():
    """Root endpoint"""
    return {"name": settings.APP_NAME, "version": settings.VERSION, "status": "running"}


@app.get("/health")
async def health_check():
    """Health check endpoint with database and Redis connectivity"""
    import asyncio

    from sqlalchemy import text

    from app.core.database import engine

    health_status = {"status": "healthy", "version": settings.VERSION, "components": {}}

    # Check database with timeout
    try:

        async def check_db():
            async with engine.begin() as conn:
                await conn.execute(text("SELECT 1"))

        await asyncio.wait_for(check_db(), timeout=5)
        health_status["components"]["database"] = "healthy"
    except asyncio.TimeoutError:
        logger.error("Database health check timed out")
        health_status["components"]["database"] = "unhealthy (timeout)"
        health_status["status"] = "degraded"
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        health_status["components"]["database"] = "unhealthy"
        health_status["status"] = "degraded"

    # Check Redis (optional) with timeout
    try:

        async def check_redis():
            import redis

            r = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            r.ping()
            r.close()

        await asyncio.wait_for(check_redis(), timeout=3)
        health_status["components"]["redis"] = "healthy"
    except asyncio.TimeoutError:
        logger.warning("Redis health check timed out")
        health_status["components"]["redis"] = "unavailable (timeout)"
    except Exception as e:
        logger.warning(f"Redis health check failed: {e}")
        health_status["components"]["redis"] = "unavailable"

    return health_status
