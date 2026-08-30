from __future__ import annotations
from contextlib import asynccontextmanager
import time
from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.api.routes import (
    weather,
    auth,
    disease,
    feedback,
    history,
    knowledge,
    query,
    translation,
    tts,
    voice,
)
from app.core.config import settings
from app.core.logging import get_logger, setup_logging
from app.database.database import check_db_connection, create_tables
from app.rag.vector_store import get_vector_store
from app.schemas.common import HealthResponse

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(debug=settings.DEBUG)
    logger.info("Starting %s v%s...", settings.APP_NAME, settings.APP_VERSION)
    logger.info("Running in %s mode (MOCK_MODE=%s)", settings.APP_ENV, settings.MOCK_MODE)

    # Initialize DB tables (in development / demo mode)
    try:
        if "sqlite" in settings.DATABASE_URL or settings.APP_ENV == "development":
            await create_tables()
    except Exception as exc:
        logger.warning("Could not auto-create DB tables on startup: %s", exc)

    # Warm up vector store
    try:
        store = get_vector_store()
        logger.info("Vector store ready: %s", store.is_ready)
    except Exception as exc:
        logger.warning("Vector store startup warning: %s", exc)

    yield

    logger.info("Shutting down %s...", settings.APP_NAME)


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Production-style backend for Multilingual AI Farmer Advisory Assistant. "
                "Supports text/voice agricultural queries, RAG context retrieval, LLM reasoning, "
                "disease detection, and 8 Indian languages.",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS Configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global Middleware: Request ID and Timing
@app.middleware("http")
async def add_process_time_and_logging(request: Request, call_next):
    start_time = time.perf_counter()
    response = await call_next(request)
    process_time = (time.perf_counter() - start_time) * 1000
    response.headers["X-Process-Time-Ms"] = f"{process_time:.2f}"
    logger.info(
        "%s %s -> %s (%.2fms)",
        request.method,
        request.url.path,
        response.status_code,
        process_time,
    )
    return response


# Global Exception Handlers
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    clean_errors = []
    for err in errors:
        clean_errors.append({
            "loc": [str(x) for x in err.get("loc", [])],
            "msg": str(err.get("msg", "")),
            "type": str(err.get("type", "")),
        })
    first_msg = clean_errors[0]["msg"] if clean_errors else "Validation error"
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "error": {
                "code": "VALIDATION_ERROR",
                "message": first_msg,
                "details": clean_errors,
            },
        },
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s", request.url.path, exc, exc_info=True)
    if settings.DEBUG:
        msg = str(exc)
    else:
        msg = "An unexpected error occurred. Please try again later."
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "success": False,
            "error": {
                "code": "INTERNAL_SERVER_ERROR",
                "message": msg,
            },
        },
    )


# Health Check
@app.get("/health", response_model=HealthResponse, tags=["System"])
async def health_check():
    from app.database.mongodb import check_mongodb_connection
    mongo_ok = await check_mongodb_connection()
    sql_ok = await check_db_connection()
    store = get_vector_store()
    
    if mongo_ok:
        db_status = "connected (mongodb)"
    elif sql_ok:
        db_status = "connected (sqlite/sql)"
    else:
        db_status = "ready (in-memory)"
        
    return HealthResponse(
        status="healthy",
        database=db_status,
        rag="ready" if store.is_ready else "not_ready",
        ai="ready (mock)" if settings.MOCK_MODE else f"ready ({settings.LLM_PROVIDER})",
        version=settings.APP_VERSION,
    )


# Register API Routers
app.include_router(auth.router, prefix=settings.API_PREFIX)
app.include_router(query.router, prefix=settings.API_PREFIX)
app.include_router(voice.router, prefix=settings.API_PREFIX)
app.include_router(disease.router, prefix=settings.API_PREFIX)
app.include_router(translation.router, prefix=settings.API_PREFIX)
app.include_router(tts.router, prefix=settings.API_PREFIX)
app.include_router(history.router, prefix=settings.API_PREFIX)
app.include_router(knowledge.router, prefix=settings.API_PREFIX)
app.include_router(feedback.router, prefix=settings.API_PREFIX)
app.include_router(weather.router, prefix=settings.API_PREFIX)



