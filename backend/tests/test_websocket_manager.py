import asyncio
import json
from unittest.mock import AsyncMock

import fakeredis.aioredis
import pytest

from app.models.extraction import ExtractionRecord, RecordType
from app.pending_queue.manager import PendingQueueManager
from app.pending_queue.websocket_manager import WebSocketManager


@pytest.fixture
async def redis_client():
    """Create a fake Redis client for testing"""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.fixture
async def queue_manager(redis_client):
    """Create a queue manager with fake Redis"""
    manager = PendingQueueManager(redis_client)
    await manager.clear()
    await manager.clear_processed_files()
    return manager


@pytest.fixture
def ws_manager():
    """Create a fresh WebSocket manager for each test"""
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection"""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_text = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_websocket_connect(ws_manager, mock_websocket):
    """Test connecting a WebSocket client"""
    await ws_manager.connect(mock_websocket)

    assert mock_websocket in ws_manager.active_connections
    assert len(ws_manager.active_connections) == 1
    mock_websocket.accept.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_disconnect(ws_manager, mock_websocket):
    """Test disconnecting a WebSocket client"""
    await ws_manager.connect(mock_websocket)
    assert len(ws_manager.active_connections) == 1

    ws_manager.disconnect(mock_websocket)

    assert mock_websocket not in ws_manager.active_connections
    assert len(ws_manager.active_connections) == 0


@pytest.mark.asyncio
async def test_websocket_broadcast_single_client(ws_manager, mock_websocket):
    """Test broadcasting a message to a single client"""
    await ws_manager.connect(mock_websocket)

    message = {"type": "record_added", "data": {"record_id": "123"}}
    await ws_manager.broadcast(message)

    mock_websocket.send_text.assert_called_once()
    sent_data = mock_websocket.send_text.call_args[0][0]
    assert json.loads(sent_data) == message


@pytest.mark.asyncio
async def test_websocket_broadcast_multiple_clients(ws_manager):
    """Test broadcasting a message to multiple clients"""
    ws1 = AsyncMock()
    ws1.accept = AsyncMock()
    ws1.send_text = AsyncMock()

    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_text = AsyncMock()

    ws3 = AsyncMock()
    ws3.accept = AsyncMock()
    ws3.send_text = AsyncMock()

    await ws_manager.connect(ws1)
    await ws_manager.connect(ws2)
    await ws_manager.connect(ws3)

    message = {"type": "record_updated", "data": {"record_id": "456"}}
    await ws_manager.broadcast(message)

    # All clients should receive the message
    ws1.send_text.assert_called_once()
    ws2.send_text.assert_called_once()
    ws3.send_text.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_broadcast_no_clients(ws_manager):
    """Test broadcasting when no clients are connected"""
    message = {"type": "record_added", "data": {"record_id": "789"}}

    # Should not raise an error
    await ws_manager.broadcast(message)


@pytest.mark.asyncio
async def test_websocket_broadcast_removes_failed_connections(ws_manager):
    """Test that failed connections are removed during broadcast"""
    ws1 = AsyncMock()
    ws1.accept = AsyncMock()
    ws1.send_text = AsyncMock()

    ws2 = AsyncMock()
    ws2.accept = AsyncMock()
    ws2.send_text = AsyncMock(side_effect=Exception("Connection lost"))

    ws3 = AsyncMock()
    ws3.accept = AsyncMock()
    ws3.send_text = AsyncMock()

    await ws_manager.connect(ws1)
    await ws_manager.connect(ws2)
    await ws_manager.connect(ws3)

    assert len(ws_manager.active_connections) == 3

    message = {"type": "test", "data": {}}
    await ws_manager.broadcast(message)

    # ws2 should be removed due to send failure
    assert len(ws_manager.active_connections) == 2
    assert ws1 in ws_manager.active_connections
    assert ws2 not in ws_manager.active_connections
    assert ws3 in ws_manager.active_connections


@pytest.mark.asyncio
async def test_queue_manager_publishes_on_add(queue_manager, redis_client):
    """Test that adding a record publishes an event"""
    # Subscribe to events before adding
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(queue_manager.PUBSUB_CHANNEL)

    # Add a record
    record = ExtractionRecord(
        type=RecordType.FORM,
        source_file="test.html",
        confidence=0.85,
        client_name="John Doe",
    )

    await queue_manager.add(record)

    # Check that event was published
    message = await pubsub.get_message(timeout=1.0)
    if message and message["type"] == "subscribe":
        message = await pubsub.get_message(timeout=1.0)

    assert message is not None
    assert message["type"] == "message"

    event_data = json.loads(message["data"])
    assert event_data["type"] == "record_added"
    assert event_data["data"]["record_id"] == record.id
    assert event_data["data"]["type"] == RecordType.FORM

    await pubsub.unsubscribe(queue_manager.PUBSUB_CHANNEL)
    await pubsub.aclose()


@pytest.mark.asyncio
async def test_queue_manager_publishes_on_remove(queue_manager, redis_client):
    """Test that removing a record publishes an event"""
    # Add a record first
    record = ExtractionRecord(
        type=RecordType.EMAIL,
        source_file="test.eml",
        confidence=0.9,
    )
    await queue_manager.add(record)

    # Subscribe to events
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(queue_manager.PUBSUB_CHANNEL)

    # Get message
    await pubsub.get_message(timeout=1.0)

    # Remove the record
    await queue_manager.remove(record.id)

    # Check that event was published
    message = await pubsub.get_message(timeout=1.0)
    assert message is not None
    assert message["type"] == "message"

    event_data = json.loads(message["data"])
    assert event_data["type"] == "record_removed"
    assert event_data["data"]["record_id"] == record.id

    await pubsub.unsubscribe(queue_manager.PUBSUB_CHANNEL)
    await pubsub.aclose()


@pytest.mark.asyncio
async def test_queue_manager_publishes_on_update(queue_manager, redis_client):
    """Test that updating a record publishes an event"""
    # Add a record first
    record = ExtractionRecord(
        type=RecordType.INVOICE,
        source_file="invoice.html",
        confidence=0.75,
        invoice_number="TF-2024-001",
    )
    await queue_manager.add(record)

    # Subscribe to events
    pubsub = redis_client.pubsub()
    await pubsub.subscribe(queue_manager.PUBSUB_CHANNEL)

    # Skip subscribe confirmation
    await pubsub.get_message(timeout=1.0)

    # Update the record
    await queue_manager.update(record.id, {"confidence": 0.95})

    # Check that event was published
    message = await pubsub.get_message(timeout=1.0)
    assert message is not None
    assert message["type"] == "message"

    event_data = json.loads(message["data"])
    assert event_data["type"] == "record_updated"
    assert event_data["data"]["record_id"] == record.id
    assert "confidence" in event_data["data"]["updates"]

    await pubsub.unsubscribe(queue_manager.PUBSUB_CHANNEL)
    await pubsub.aclose()


@pytest.mark.asyncio
async def test_subscribe_to_events(queue_manager):
    """Test subscribing to queue events"""

    # Create a task to add records after a short delay
    async def add_records():
        await asyncio.sleep(0.1)
        record1 = ExtractionRecord(
            type=RecordType.FORM,
            source_file="form1.html",
            confidence=0.8,
        )
        await queue_manager.add(record1)

        await asyncio.sleep(0.1)
        record2 = ExtractionRecord(
            type=RecordType.EMAIL,
            source_file="email1.eml",
            confidence=0.9,
        )
        await queue_manager.add(record2)

    # Start adding records in background
    add_task = asyncio.create_task(add_records())

    # Subscribe and collect events
    events = []
    async for event in queue_manager.subscribe_to_events():
        events.append(event)
        if len(events) >= 2:
            break

    await add_task

    # Verify we received both events
    assert len(events) == 2
    assert events[0]["type"] == "record_added"
    assert events[1]["type"] == "record_added"


@pytest.mark.asyncio
async def test_websocket_integration_with_queue(queue_manager, ws_manager, mock_websocket):
    """Test full integration: queue events -> WebSocket broadcast"""
    # Connect a WebSocket client
    await ws_manager.connect(mock_websocket)

    # Start broadcasting (this will subscribe to queue events)
    broadcast_task = asyncio.create_task(ws_manager.start_broadcasting(queue_manager))

    # Give it time to start
    await asyncio.sleep(0.1)

    # Add a record to the queue
    record = ExtractionRecord(
        type=RecordType.FORM,
        source_file="test.html",
        confidence=0.85,
        client_name="Jane Doe",
    )
    await queue_manager.add(record)

    # Give time for event to propagate
    await asyncio.sleep(0.2)

    # Stop broadcasting
    await ws_manager.stop_broadcasting()
    broadcast_task.cancel()
    try:
        await broadcast_task
    except asyncio.CancelledError:
        pass

    # Verify WebSocket received the event
    assert mock_websocket.send_text.called
    sent_data = mock_websocket.send_text.call_args[0][0]
    event = json.loads(sent_data)
    assert event["type"] == "record_added"
    assert event["data"]["record_id"] == record.id


@pytest.mark.asyncio
async def test_stop_broadcasting(ws_manager, queue_manager):
    """Test stopping the broadcast task"""
    await ws_manager.start_broadcasting(queue_manager)

    assert ws_manager._broadcast_task is not None
    assert not ws_manager._broadcast_task.done()

    await ws_manager.stop_broadcasting()

    assert ws_manager._broadcast_task.done()
