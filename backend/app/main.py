from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes
from app.config import get_settings
from app.integrations.sheets import GoogleSheetsClient
from app.pending_queue.manager import PendingQueueManager
from app.pending_queue.redis_client import RedisClient
from app.pending_queue.websocket_manager import ws_manager
from app.services.extraction import ExtractionService

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
            redis_url=settings.redis_url,
            google_credentials_path=settings.google_credentials_path,
            google_spreadsheet_id=settings.google_spreadsheet_id,
        )

        # Initialize Redis client
        redis_client = await RedisClient.get_client(settings)
        logger.info("redis_connected")

        # Initialize queue manager
        queue_manager = PendingQueueManager(redis_client)
        logger.info("queue_manager_initialized")

        # Initialize extraction service
        extraction_service = ExtractionService(queue_manager)
        logger.info("extraction_service_initialized")

        # Initialize Google Sheets client
        sheets_client = GoogleSheetsClient(
            credentials_path=settings.google_credentials_path,
            spreadsheet_id=settings.google_spreadsheet_id,
        )
        logger.info("sheets_client_initialized")

        # Inject services into routes
        routes.set_services(queue_manager, extraction_service, sheets_client)
        logger.info("services_injected_into_routes")

        # Start WebSocket broadcasting
        await ws_manager.start_broadcasting(queue_manager)
        logger.info("websocket_broadcasting_started")

    except Exception as e:
        logger.error("startup_failed", error=str(e))
        raise

    yield

    # Shutdown
    try:
        await ws_manager.stop_broadcasting()
        await RedisClient.close()
        logger.info("application_shutdown")
    except Exception as e:
        logger.error("shutdown_error", error=str(e))


app = FastAPI(
    title="TechFlow Automation Platform API",
    description="Automated client data extraction and management system",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS
settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(routes.router)
