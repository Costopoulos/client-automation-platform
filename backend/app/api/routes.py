from pathlib import Path
from typing import Any, Dict

import structlog
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from app.integrations.sheets import GoogleSheetsClient
from app.models.extraction import ApprovalResult, RecordType, ScanResult
from app.pending_queue.manager import PendingQueueManager
from app.pending_queue.websocket_manager import ws_manager
from app.services.extraction import ExtractionService

logger = structlog.get_logger()

# Create API router
router = APIRouter(prefix="/api")

# Global service instances (will be set by main.py during startup)
queue_manager: PendingQueueManager = None
extraction_service: ExtractionService = None
sheets_client: GoogleSheetsClient = None


def set_services(
    queue_mgr: PendingQueueManager,
    extraction_svc: ExtractionService,
    sheets_cli: GoogleSheetsClient,
):
    """
    Set service instances for use in route handlers

    This is called during application startup to inject dependencies.
    """
    global queue_manager, extraction_service, sheets_client
    queue_manager = queue_mgr
    extraction_service = extraction_svc
    sheets_client = sheets_cli


@router.get("/health")
async def health():
    """
    Health check endpoint with system statistics

    Returns system status and statistics about the queue and processing.
    """
    try:
        # Check Redis health
        redis_healthy = await queue_manager.health_check()

        # Get queue statistics
        pending_count = await queue_manager.get_count()

        return {
            "status": "healthy" if redis_healthy else "degraded",
            "redis": "connected" if redis_healthy else "disconnected",
            "stats": {
                "pending_count": pending_count,
            },
        }
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        return {
            "status": "unhealthy",
            "error": str(e),
        }


@router.post("/scan")
async def scan_files() -> ScanResult:
    """
    Trigger file scanning and extraction

    Scans source directories for new unprocessed files, extracts data,
    and adds extraction records to the pending queue.

    Returns:
        ScanResult with counts of processed, new, and failed files
    """
    try:
        logger.info("scan_endpoint_called")
        result = await extraction_service.scan_and_extract()
        logger.info(
            "scan_endpoint_completed",
            processed=result.processed_count,
            new_items=result.new_items_count,
            failed=result.failed_count,
        )
        return result
    except Exception as e:
        logger.error("scan_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Scan failed: {str(e)}")


@router.get("/pending")
async def get_pending():
    """
    Get all pending extraction records

    Returns:
        List of all extraction records awaiting review
    """
    try:
        records = await queue_manager.list_all()
        logger.info("pending_endpoint_called", count=len(records))
        return records
    except Exception as e:
        logger.error("pending_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch pending records: {str(e)}")


@router.get("/pending/count")
async def get_pending_count():
    """
    Get count of pending records

    Returns:
        Count of pending items in the queue
    """
    try:
        count = await queue_manager.get_count()
        return {"count": count, "has_new": count > 0}
    except Exception as e:
        logger.error("pending_count_endpoint_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to fetch pending count: {str(e)}")


@router.delete("/pending/clear")
async def clear_pending_queue():
    """
    Clear all pending records from the queue (for testing/development)

    Returns:
        Success status with count of cleared records
    """
    try:
        # Get count before clearing
        count_before = await queue_manager.get_count()

        # Clear the queue
        await queue_manager.clear()

        # Also clear processed files tracking
        await queue_manager.clear_processed_files()

        logger.info("queue_cleared", records_cleared=count_before)

        return {
            "success": True,
            "message": "Queue cleared successfully",
            "records_cleared": count_before,
        }
    except Exception as e:
        logger.error("clear_queue_error", error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to clear queue: {str(e)}")


@router.post("/approve/{record_id}")
async def approve_record(record_id: str) -> ApprovalResult:
    """
    Approve an extraction record, write to Google Sheets and remove from queue

    Args:
        record_id: ID of the record to approve

    Returns:
        ApprovalResult with success status and sheet row number
    """
    try:
        logger.info("approve_endpoint_called", record_id=record_id)

        # Get the record
        record = await queue_manager.get_by_id(record_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Record {record_id} not found")

        # Write to appropriate Google Sheets sheet
        # Route based on whether record contains invoice data, not just type
        # since emails can contain invoice information
        try:
            if record.type == RecordType.INVOICE or record.invoice_number:
                row_number = sheets_client.write_invoice_record(record)
            else:  # FORM or EMAIL without invoice data
                row_number = sheets_client.write_client_record(record)

            # Remove from pending queue
            await queue_manager.remove(record_id)

            logger.info(
                "record_approved",
                record_id=record_id,
                record_type=record.type,
                row_number=row_number,
            )

            return ApprovalResult(success=True, sheet_row=row_number)

        except Exception as e:
            logger.error(
                "approval_sheets_write_failed",
                record_id=record_id,
                error=str(e),
            )
            return ApprovalResult(
                success=False,
                error=f"Failed to write to Google Sheets: {str(e)}",
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("approve_endpoint_error", record_id=record_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Approval failed: {str(e)}")


@router.post("/reject/{record_id}")
async def reject_record(record_id: str):
    """
    Reject an extraction record and remove from queue

    Args:
        record_id: ID of the record to reject

    Returns:
        Success status
    """
    try:
        logger.info("reject_endpoint_called", record_id=record_id)

        # Check if record exists
        record = await queue_manager.get_by_id(record_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Record {record_id} not found")

        # Remove from queue
        await queue_manager.remove(record_id)

        logger.info("record_rejected", record_id=record_id)

        return {"success": True, "message": f"Record {record_id} rejected"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error("reject_endpoint_error", record_id=record_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Rejection failed: {str(e)}")


@router.patch("/edit/{record_id}")
async def edit_record(record_id: str, updates: Dict[str, Any]):
    """
    Update fields in an extraction record

    Args:
        record_id: ID of the record to update
        updates: Dictionary of field names and new values

    Returns:
        Updated extraction record
    """
    try:
        logger.info("edit_endpoint_called", record_id=record_id, fields=list(updates.keys()))

        # Check if record exists
        record = await queue_manager.get_by_id(record_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Record {record_id} not found")

        # Update the record
        updated_record = await queue_manager.update(record_id, updates)

        logger.info(
            "record_updated",
            record_id=record_id,
            updated_fields=list(updates.keys()),
        )

        return updated_record

    except HTTPException:
        raise
    except Exception as e:
        logger.error("edit_endpoint_error", record_id=record_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Edit failed: {str(e)}")


@router.get("/source/{record_id}")
async def get_source(record_id: str):
    """
    Get original source file content for a record

    Args:
        record_id: ID of the record

    Returns:
        Source file content and type
    """
    try:
        logger.info("source_endpoint_called", record_id=record_id)

        # Get the record
        record = await queue_manager.get_by_id(record_id)
        if not record:
            raise HTTPException(status_code=404, detail=f"Record {record_id} not found")

        # Read source file
        source_path = Path(record.source_file)
        if not source_path.exists():
            raise HTTPException(
                status_code=404, detail=f"Source file not found: {record.source_file}"
            )

        # Read file content
        content = source_path.read_text(encoding="utf-8")

        # Determine content type
        content_type = "text/html" if source_path.suffix == ".html" else "text/plain"

        logger.info(
            "source_file_retrieved",
            record_id=record_id,
            source_file=record.source_file,
            content_length=len(content),
        )

        return {
            "content": content,
            "type": content_type,
            "filename": source_path.name,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error("source_endpoint_error", record_id=record_id, error=str(e))
        raise HTTPException(status_code=500, detail=f"Failed to retrieve source: {str(e)}")


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time queue event notifications

    Clients connect to this endpoint to receive real-time updates about
    queue events (record_added, record_removed, record_updated).
    """
    await ws_manager.connect(websocket)
    logger.info("websocket_client_connected")

    try:
        # Keep connection alive and listen for client messages (if any)
        while True:
            # Wait for any message from client (ping/pong)
            await websocket.receive_text()

    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
        logger.info("websocket_client_disconnected")
    except Exception as e:
        logger.error("websocket_error", error=str(e))
        ws_manager.disconnect(websocket)
