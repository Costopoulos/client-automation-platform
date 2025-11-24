import fakeredis.aioredis
import pytest

from app.models.extraction import ExtractionRecord, RecordType
from app.pending_queue.manager import PendingQueueManager


@pytest.fixture
async def redis_client():
    """Create a fake Redis client for testing"""
    client = fakeredis.aioredis.FakeRedis(decode_responses=True)
    yield client
    await client.flushall()
    await client.aclose()


@pytest.fixture
async def queue_manager(redis_client):
    """Create a fresh queue manager for each test"""
    manager = PendingQueueManager(redis_client)
    # Clear any existing data
    await manager.clear()
    await manager.clear_processed_files()
    return manager


@pytest.fixture
def sample_record():
    """Create a sample extraction record"""
    return ExtractionRecord(
        type=RecordType.FORM,
        source_file="test_form.html",
        confidence=0.85,
        client_name="John Doe",
        email="john@example.com",
        phone="+30 210 1234567",
    )


@pytest.mark.asyncio
async def test_add_record(queue_manager, sample_record):
    """Test adding a record to the queue"""
    await queue_manager.add(sample_record)

    # Verify record was added
    retrieved = await queue_manager.get_by_id(sample_record.id)
    assert retrieved is not None
    assert retrieved.id == sample_record.id
    assert retrieved.client_name == "John Doe"


@pytest.mark.asyncio
async def test_add_duplicate_record_raises_error(queue_manager, sample_record):
    """Test that adding a duplicate record raises ValueError"""
    await queue_manager.add(sample_record)

    with pytest.raises(ValueError, match="already exists"):
        await queue_manager.add(sample_record)


@pytest.mark.asyncio
async def test_remove_record(queue_manager, sample_record):
    """Test removing a record from the queue"""
    await queue_manager.add(sample_record)
    await queue_manager.remove(sample_record.id)

    # Verify record was removed
    retrieved = await queue_manager.get_by_id(sample_record.id)
    assert retrieved is None


@pytest.mark.asyncio
async def test_remove_nonexistent_record_raises_error(queue_manager):
    """Test that removing a non-existent record raises KeyError"""
    with pytest.raises(KeyError, match="not found"):
        await queue_manager.remove("nonexistent-id")


@pytest.mark.asyncio
async def test_update_record(queue_manager, sample_record):
    """Test updating fields in a record"""
    await queue_manager.add(sample_record)

    updates = {
        "client_name": "Jane Smith",
        "phone": "+30 210 9876543",
        "confidence": 0.95,
    }

    updated = await queue_manager.update(sample_record.id, updates)

    assert updated.client_name == "Jane Smith"
    assert updated.phone == "+30 210 9876543"
    assert updated.confidence == 0.95
    # Original fields should remain
    assert updated.email == "john@example.com"
    assert updated.type == RecordType.FORM


@pytest.mark.asyncio
async def test_update_nonexistent_record_raises_error(queue_manager):
    """Test that updating a non-existent record raises KeyError"""
    with pytest.raises(KeyError, match="not found"):
        await queue_manager.update("nonexistent-id", {"client_name": "Test"})


@pytest.mark.asyncio
async def test_list_all_empty(queue_manager):
    """Test listing all records when queue is empty"""
    records = await queue_manager.list_all()
    assert records == []


@pytest.mark.asyncio
async def test_list_all_multiple_records(queue_manager):
    """Test listing all records with multiple items"""
    record1 = ExtractionRecord(
        type=RecordType.FORM,
        source_file="form1.html",
        confidence=0.8,
        client_name="Alice",
    )
    record2 = ExtractionRecord(
        type=RecordType.EMAIL,
        source_file="email1.eml",
        confidence=0.9,
        client_name="Bob",
    )
    record3 = ExtractionRecord(
        type=RecordType.INVOICE,
        source_file="invoice1.html",
        confidence=0.95,
        invoice_number="TF-2024-001",
    )

    await queue_manager.add(record1)
    await queue_manager.add(record2)
    await queue_manager.add(record3)

    records = await queue_manager.list_all()
    assert len(records) == 3

    # Verify all records are present
    record_ids = {r.id for r in records}
    assert record1.id in record_ids
    assert record2.id in record_ids
    assert record3.id in record_ids


@pytest.mark.asyncio
async def test_get_by_id_existing(queue_manager, sample_record):
    """Test getting a record by ID when it exists"""
    await queue_manager.add(sample_record)

    retrieved = await queue_manager.get_by_id(sample_record.id)
    assert retrieved is not None
    assert retrieved.id == sample_record.id
    assert retrieved.client_name == sample_record.client_name


@pytest.mark.asyncio
async def test_get_by_id_nonexistent(queue_manager):
    """Test getting a record by ID when it doesn't exist"""
    retrieved = await queue_manager.get_by_id("nonexistent-id")
    assert retrieved is None


@pytest.mark.asyncio
async def test_mark_file_processed(queue_manager):
    """Test marking a file as processed"""
    filepath = "/path/to/file.html"

    assert not await queue_manager.is_file_processed(filepath)

    await queue_manager.mark_file_processed(filepath)

    assert await queue_manager.is_file_processed(filepath)


@pytest.mark.asyncio
async def test_is_file_processed_multiple_files(queue_manager):
    """Test tracking multiple processed files"""
    file1 = "/path/to/file1.html"
    file2 = "/path/to/file2.html"
    file3 = "/path/to/file3.html"

    await queue_manager.mark_file_processed(file1)
    await queue_manager.mark_file_processed(file2)

    assert await queue_manager.is_file_processed(file1)
    assert await queue_manager.is_file_processed(file2)
    assert not await queue_manager.is_file_processed(file3)


@pytest.mark.asyncio
async def test_mark_file_processed_idempotent(queue_manager):
    """Test that marking a file as processed multiple times is safe"""
    filepath = "/path/to/file.html"

    await queue_manager.mark_file_processed(filepath)
    await queue_manager.mark_file_processed(filepath)
    await queue_manager.mark_file_processed(filepath)

    assert await queue_manager.is_file_processed(filepath)


@pytest.mark.asyncio
async def test_get_count_empty(queue_manager):
    """Test getting count when queue is empty"""
    count = await queue_manager.get_count()
    assert count == 0


@pytest.mark.asyncio
async def test_get_count_with_records(queue_manager, sample_record):
    """Test getting count with records in queue"""
    await queue_manager.add(sample_record)
    count = await queue_manager.get_count()
    assert count == 1

    record2 = ExtractionRecord(
        type=RecordType.EMAIL,
        source_file="email.eml",
        confidence=0.9,
    )
    await queue_manager.add(record2)
    count = await queue_manager.get_count()
    assert count == 2


@pytest.mark.asyncio
async def test_clear_queue(queue_manager, sample_record):
    """Test clearing all records from the queue"""
    await queue_manager.add(sample_record)
    record2 = ExtractionRecord(
        type=RecordType.EMAIL,
        source_file="email.eml",
        confidence=0.9,
    )
    await queue_manager.add(record2)

    assert await queue_manager.get_count() == 2

    await queue_manager.clear()

    assert await queue_manager.get_count() == 0
    records = await queue_manager.list_all()
    assert records == []


@pytest.mark.asyncio
async def test_thread_safety_concurrent_adds(queue_manager):
    """Test that concurrent add operations are thread-safe"""
    import asyncio

    async def add_record(index):
        record = ExtractionRecord(
            type=RecordType.FORM,
            source_file=f"form_{index}.html",
            confidence=0.8,
            client_name=f"Client {index}",
        )
        await queue_manager.add(record)

    # Add 10 records concurrently
    await asyncio.gather(*[add_record(i) for i in range(10)])

    count = await queue_manager.get_count()
    assert count == 10


@pytest.mark.asyncio
async def test_thread_safety_concurrent_operations(queue_manager):
    """Test that mixed concurrent operations are thread-safe"""
    import asyncio

    # Add initial records
    records = []
    for i in range(5):
        record = ExtractionRecord(
            type=RecordType.FORM,
            source_file=f"form_{i}.html",
            confidence=0.8,
            client_name=f"Client {i}",
        )
        await queue_manager.add(record)
        records.append(record)

    async def update_record(record):
        await queue_manager.update(record.id, {"confidence": 0.95})

    async def remove_record(record):
        await queue_manager.remove(record.id)

    async def list_records():
        await queue_manager.list_all()

    # Perform mixed operations concurrently
    operations = []
    operations.extend([update_record(records[0]), update_record(records[1])])
    operations.extend([remove_record(records[2]), remove_record(records[3])])
    operations.extend([list_records() for _ in range(5)])

    await asyncio.gather(*operations)

    # Verify final state
    count = await queue_manager.get_count()
    assert count == 3  # Started with 5, removed 2

    # Verify updates were applied
    updated1 = await queue_manager.get_by_id(records[0].id)
    assert updated1.confidence == 0.95


@pytest.mark.asyncio
async def test_health_check(queue_manager):
    """Test Redis health check"""
    is_healthy = await queue_manager.health_check()
    assert is_healthy is True


@pytest.mark.asyncio
async def test_clear_processed_files(queue_manager):
    """Test clearing processed files tracking"""
    file1 = "/path/to/file1.html"
    file2 = "/path/to/file2.html"

    await queue_manager.mark_file_processed(file1)
    await queue_manager.mark_file_processed(file2)

    assert await queue_manager.is_file_processed(file1)
    assert await queue_manager.is_file_processed(file2)

    await queue_manager.clear_processed_files()

    assert not await queue_manager.is_file_processed(file1)
    assert not await queue_manager.is_file_processed(file2)


@pytest.mark.asyncio
async def test_persistence_simulation(queue_manager, redis_client):
    """Test that data persists across manager instances (simulating server restart)"""
    # Add records with first manager instance
    record1 = ExtractionRecord(
        type=RecordType.FORM,
        source_file="form.html",
        confidence=0.85,
        client_name="John Doe",
    )
    await queue_manager.add(record1)
    await queue_manager.mark_file_processed("form.html")

    # Create new manager instance with same Redis client (simulating restart)
    new_manager = PendingQueueManager(redis_client)

    # Verify data persists
    retrieved = await new_manager.get_by_id(record1.id)
    assert retrieved is not None
    assert retrieved.client_name == "John Doe"

    assert await new_manager.is_file_processed("form.html")

    count = await new_manager.get_count()
    assert count == 1
