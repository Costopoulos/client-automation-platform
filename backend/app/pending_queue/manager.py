import json
from typing import List, Optional

import redis.asyncio as redis

from app.models.extraction import ExtractionRecord


class PendingQueueManager:
    """
    Manages the pending queue of extraction records using Redis.

    This class provides thread-safe operations for managing extraction records
    that are awaiting human review and approval. It also tracks processed files
    to prevent duplicate processing.

    Redis provides:
    - Atomic operations (no need for manual locking)
    - Persistence (survives server restarts)
    - Production-ready scalability
    - Fast O(1) lookups
    - Pub/Sub for real-time notifications

    """

    # Redis key prefixes
    QUEUE_PREFIX = "queue:record:"  # individual records
    PROCESSED_FILES_KEY = "queue:processed_files"  # set of files processed
    QUEUE_IDS_KEY = "queue:record_ids"  # set of all record ids, eg for listing all items -> Redis doesn't support "get all keys with prefix" well
    PUBSUB_CHANNEL = "queue:events"  # pub/sub channel for real-time updates

    def __init__(self, redis_client: redis.Redis):
        """
        Initialize the pending queue manager with Redis client.

        Args:
            redis_client: Async Redis client instance
        """
        self._redis = redis_client

    async def add(self, record: ExtractionRecord) -> None:
        """
        Add an extraction record to the pending queue.

        Args:
            record: The extraction record to add

        Raises:
            ValueError: If a record with the same ID already exists
        """
        record_key = f"{self.QUEUE_PREFIX}{record.id}"

        # Check if record already exists
        exists = await self._redis.exists(record_key)
        if exists:
            raise ValueError(f"Record with ID {record.id} already exists in queue")

        # Store record as JSON
        record_json = record.model_dump_json()

        # Use pipeline for atomic operations
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.set(record_key, record_json)
            pipe.sadd(self.QUEUE_IDS_KEY, record.id)
            await pipe.execute()

        # Publish event for real-time updates
        await self._publish_event(
            "record_added",
            {
                "record_id": record.id,
                "type": record.type,
                "confidence": record.confidence,
            },
        )

    async def remove(self, record_id: str) -> None:
        """
        Remove an extraction record from the pending queue.

        Args:
            record_id: The ID of the record to remove

        Raises:
            KeyError: If the record ID does not exist in the queue
        """
        record_key = f"{self.QUEUE_PREFIX}{record_id}"

        # Check if record exists
        exists = await self._redis.exists(record_key)
        if not exists:
            raise KeyError(f"Record with ID {record_id} not found in queue")

        # Use pipeline for atomic operations
        async with self._redis.pipeline(transaction=True) as pipe:
            pipe.delete(record_key)
            pipe.srem(self.QUEUE_IDS_KEY, record_id)
            await pipe.execute()

        # Publish event for real-time updates
        await self._publish_event("record_removed", {"record_id": record_id})

    async def update(self, record_id: str, updates: dict) -> ExtractionRecord:
        """
        Update fields in an extraction record.

        Args:
            record_id: The ID of the record to update
            updates: Dictionary of field names and new values

        Returns:
            The updated extraction record

        Raises:
            KeyError: If the record ID does not exist in the queue
        """
        record_key = f"{self.QUEUE_PREFIX}{record_id}"

        # Get existing record
        record_json = await self._redis.get(record_key)
        if not record_json:
            raise KeyError(f"Record with ID {record_id} not found in queue")

        # Parse and update
        record_data = json.loads(record_json)
        record_data.update(updates)
        updated_record = ExtractionRecord(**record_data)

        # Save updated record
        await self._redis.set(record_key, updated_record.model_dump_json())

        # Publish event for real-time updates
        await self._publish_event(
            "record_updated",
            {
                "record_id": record_id,
                "updates": list(updates.keys()),
            },
        )

        return updated_record

    async def list_all(self) -> List[ExtractionRecord]:
        """
        Get all pending extraction records.

        Returns:
            List of all extraction records in the queue
        """
        # Get all record IDs
        record_ids = await self._redis.smembers(self.QUEUE_IDS_KEY)

        if not record_ids:
            return []

        # Fetch all records in parallel
        record_keys = [f"{self.QUEUE_PREFIX}{record_id}" for record_id in record_ids]
        record_jsons = await self._redis.mget(record_keys)

        # Parse records
        records = []
        for record_json in record_jsons:
            if record_json:
                record_data = json.loads(record_json)
                records.append(ExtractionRecord(**record_data))

        return records

    async def get_by_id(self, record_id: str) -> Optional[ExtractionRecord]:
        """
        Get a specific extraction record by ID.

        Args:
            record_id: The ID of the record to retrieve

        Returns:
            The extraction record if found, None otherwise
        """
        record_key = f"{self.QUEUE_PREFIX}{record_id}"
        record_json = await self._redis.get(record_key)

        if not record_json:
            return None

        record_data = json.loads(record_json)
        return ExtractionRecord(**record_data)

    async def mark_file_processed(self, filepath: str) -> None:
        """
        Mark a file as processed to prevent duplicate processing.

        Args:
            filepath: The path of the file to mark as processed
        """
        await self._redis.sadd(self.PROCESSED_FILES_KEY, filepath)

    async def is_file_processed(self, filepath: str) -> bool:
        """
        Check if a file has already been processed.

        Args:
            filepath: The path of the file to check

        Returns:
            True if the file has been processed, False otherwise
        """
        return await self._redis.sismember(self.PROCESSED_FILES_KEY, filepath)

    async def get_count(self) -> int:
        """
        Get the count of pending records in the queue.

        Returns:
            Number of records in the queue
        """
        return await self._redis.scard(self.QUEUE_IDS_KEY)

    async def clear(self) -> None:
        """
        Clear all records from the queue.

        This is primarily useful for testing or administrative purposes.
        """
        # Get all record IDs
        record_ids = await self._redis.smembers(self.QUEUE_IDS_KEY)

        if record_ids:
            # Delete all record keys
            record_keys = [f"{self.QUEUE_PREFIX}{record_id}" for record_id in record_ids]
            async with self._redis.pipeline(transaction=True) as pipe:
                for key in record_keys:
                    pipe.delete(key)
                pipe.delete(self.QUEUE_IDS_KEY)
                await pipe.execute()
        else:
            # Just delete the IDs set if it exists
            await self._redis.delete(self.QUEUE_IDS_KEY)

    async def clear_processed_files(self) -> None:
        """
        Clear the processed files tracking.

        This is primarily useful for testing or reprocessing files.
        """
        await self._redis.delete(self.PROCESSED_FILES_KEY)

    async def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.

        Returns:
            True if Redis is accessible, False otherwise
        """
        try:
            await self._redis.ping()
            return True
        except Exception:
            return False

    async def _publish_event(self, event_type: str, data: dict) -> None:
        """
        Publish an event to the Redis pub/sub channel.

        Args:
            event_type: Type of event (record_added, record_removed, record_updated)
            data: Event data to publish
        """
        event = {
            "type": event_type,
            "data": data,
        }
        await self._redis.publish(self.PUBSUB_CHANNEL, json.dumps(event))

    async def subscribe_to_events(self):
        """
        Subscribe to queue events for real-time updates.

        Returns:
            Async generator yielding events as they occur

        Usage:
            async for event in queue_manager.subscribe_to_events():
                print(f"Event: {event}")
        """
        pubsub = self._redis.pubsub()
        await pubsub.subscribe(self.PUBSUB_CHANNEL)

        try:
            async for message in pubsub.listen():
                if message["type"] == "message":
                    event_data = json.loads(message["data"])
                    yield event_data
        finally:
            await pubsub.unsubscribe(self.PUBSUB_CHANNEL)
            await pubsub.aclose()
