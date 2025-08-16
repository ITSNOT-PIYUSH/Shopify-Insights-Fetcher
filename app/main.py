"""
Main FastAPI application for Shopify Insights Fetcher.
"""
import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.utils import setup_logging
from app.models.schemas import HealthCheckResponse, ErrorResponse
from app.api.routes import router as api_router
from app.db.database import init_db, get_db_health

# Setup logging
setup_logging(debug=settings.debug)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events."""
    # Startup
    logger.info("🚀 Starting Shopify Insights Fetcher application...")
    
    # Initialize database
    try:
        init_db()
        logger.info("✅ Database initialization completed")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")
    
    yield
    
    # Shutdown
    logger.info("👋 Shutting down Shopify Insights Fetcher application...")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="A comprehensive API for extracting insights from Shopify stores",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Middleware for request timing
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    """Add processing time to response headers."""
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


# Global exception handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail or "HTTP Error",
            status_code=exc.status_code
        ).model_dump()
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=ErrorResponse(
            error="Internal Server Error",
            detail=str(exc) if settings.debug else "An unexpected error occurred",
            status_code=500
        ).model_dump()
    )


# Health check endpoint
@app.get(
    "/health",
    response_model=HealthCheckResponse,
    summary="Health Check",
    description="Check the health status of the application and its dependencies"
)
async def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        db_healthy = get_db_health()
        
        return HealthCheckResponse(
            status="healthy",
            version=settings.app_version,
            database_connected=db_healthy
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail="Service temporarily unavailable"
        )


# Root endpoint
@app.get(
    "/",
    summary="Root Endpoint",
    description="Welcome message and basic API information"
)
async def root():
    """Root endpoint with welcome message."""
    return {
        "message": f"Welcome to {settings.app_name}",
        "version": settings.app_version,
        "docs_url": "/docs",
        "health_check": "/health"
    }


# Include API routes
app.include_router(
    api_router,
    prefix="/api/v1",
    tags=["insights"]
)


if __name__ == "__main__":
    import uvicorn
    
    logger.info(f"Starting {settings.app_name} on {settings.api_host}:{settings.api_port}")
    
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level="debug" if settings.debug else "info"
    )
