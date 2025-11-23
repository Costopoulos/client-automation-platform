from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings

logger = structlog.get_logger()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for startup and shutdown"""
    # Startup
    try:
        settings = get_settings()
        logger.info(
            "application_startup",
            base_dir=settings.base_dir,
            forms_dir=settings.forms_dir,
            emails_dir=settings.emails_dir,
            invoices_dir=settings.invoices_dir,
            openai_model=settings.openai_model,
            log_level=settings.log_level,
        )
    except Exception as e:
        logger.error("startup_failed", error=str(e))
        raise

    yield

    # Shutdown (if needed in the future)
    logger.info("application_shutdown")


app = FastAPI(
    title="TechFlow Automation Platform API",
    description="Automated client data extraction and management system",
    version="0.1.0",
    lifespan=lifespan,
)


# Configure CORS with settings
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
async def health():
    return {"status": "healthy"}
