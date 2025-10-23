"""
Hashing Utilities

Functions for generating payload hashes for execution deduplication.
"""

import hashlib
import json
from datetime import datetime, date
from decimal import Decimal
from typing import Any


def json_serial(obj: Any) -> Any:
    """
    JSON serializer for objects not serializable by default json code.

    Handles:
    - datetime objects (converts to ISO format)
    - date objects (converts to ISO format)
    - Decimal objects (converts to float)

    Args:
        obj: Object to serialize

    Returns:
        Serializable representation

    Raises:
        TypeError: If type is not serializable
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    if isinstance(obj, date):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def generate_payload_hash(
    payload: dict[str, Any], processor_triggers: dict[str, list[str]] | None = None
) -> str:
    """
    Generate SHA256 hash from payload for deduplication.

    Creates a deterministic hash by:
    1. Extracting only trigger-specified fields (if processor_triggers provided)
    2. Normalizing the payload structure (sorting keys recursively)
    3. Converting to JSON with lexicographically sorted keys
    4. Handling special types (datetime, Decimal)
    5. Computing SHA256 hash of the canonical JSON string

    The hash is consistent regardless of:
    - Dictionary key insertion order
    - Nested dictionary key order
    - Dictionary keys within lists

    Note: List item order is preserved (semantic order matters for lists).

    Args:
        payload: Execution payload dictionary
        processor_triggers: Optional processor triggers to filter which fields to hash

    Returns:
        SHA256 hash of the payload as hexadecimal string

    Example:
        >>> payload1 = {"b": 2, "a": 1, "c": 3}
        >>> payload2 = {"a": 1, "b": 2, "c": 4}
        >>> triggers = {"application_form": ["a", "b"]}
        >>> generate_payload_hash(payload1, triggers) == generate_payload_hash(payload2, triggers)
        True  # Only "a" and "b" are hashed, "c" is ignored
    """
    # Extract only trigger fields if processor_triggers provided
    if processor_triggers:
        payload = _extract_trigger_fields(payload, processor_triggers)

    # Normalize payload first (handles nested structures)
    normalized = _normalize_for_hashing(payload)

    # Convert to JSON with sorted keys (lexicographic order)
    # This ensures consistent serialization regardless of insertion order
    payload_str = json.dumps(normalized, sort_keys=True, default=json_serial)

    # Generate SHA256 hash
    payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

    return payload_hash


def _extract_trigger_fields(
    payload: dict[str, Any], processor_triggers: dict[str, list[str]]
) -> dict[str, Any]:
    """
    Extract only the fields specified in processor triggers from payload.

    This ensures the hash only changes when trigger-relevant fields change.

    Args:
        payload: Full execution payload
        processor_triggers: Processor triggers specifying which fields to include

    Returns:
        Filtered payload containing only trigger fields
    """
    filtered_payload = {}

    # Handle application_form triggers
    if "application_form" in processor_triggers and "application_form" in payload:
        trigger_fields = processor_triggers["application_form"]
        app_form = payload["application_form"]
        filtered_app_form = {
            field: app_form.get(field) for field in trigger_fields if field in app_form
        }
        if filtered_app_form:
            filtered_payload["application_form"] = filtered_app_form

    # Handle documents_list triggers
    if "documents_list" in processor_triggers and "revision_id" in payload:
        # For document-based processors, include the revision_id(s)
        filtered_payload["revision_id"] = payload["revision_id"]

    return filtered_payload


def _normalize_for_hashing(obj: Any) -> Any:
    """
    Recursively normalize data structures for consistent hashing.

    Ensures:
    - Dictionary keys are processed in consistent order
    - Nested dictionaries are normalized recursively
    - Lists preserve order but dictionaries within are normalized
    - None values are preserved

    Args:
        obj: Any object to normalize

    Returns:
        Normalized object ready for JSON serialization
    """
    if isinstance(obj, dict):
        # Recursively normalize dictionary values
        # Keys will be sorted during JSON serialization
        return {key: _normalize_for_hashing(value) for key, value in obj.items()}

    elif isinstance(obj, list):
        # Preserve list order (semantic order matters)
        # But normalize items within the list
        return [_normalize_for_hashing(item) for item in obj]

    elif isinstance(obj, tuple):
        # Convert tuples to lists for consistent serialization
        return [_normalize_for_hashing(item) for item in obj]

    elif isinstance(obj, set):
        # Convert sets to sorted lists for consistent hashing
        # Sets have no inherent order, so we sort for consistency
        return sorted([_normalize_for_hashing(item) for item in obj])

    else:
        # Primitive types, datetime, Decimal handled by json_serial
        return obj
