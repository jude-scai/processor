"""
Hashing Utilities

Functions for generating payload hashes for execution deduplication.
"""

import hashlib
import json
from datetime import datetime
from decimal import Decimal
from typing import Any


def json_serial(obj: Any) -> Any:
    """
    JSON serializer for objects not serializable by default json code.
    
    Handles:
    - datetime objects (converts to ISO format)
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
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError(f"Type {type(obj)} not serializable")


def generate_payload_hash(payload: dict[str, Any]) -> str:
    """
    Generate SHA256 hash from payload for deduplication.
    
    Creates a deterministic hash by:
    1. Normalizing the payload structure (sorting keys recursively)
    2. Converting to JSON with lexicographically sorted keys
    3. Handling special types (datetime, Decimal)
    4. Computing SHA256 hash of the canonical JSON string
    
    The hash is consistent regardless of:
    - Dictionary key insertion order
    - Nested dictionary key order
    - Dictionary keys within lists
    
    Note: List item order is preserved (semantic order matters for lists).
    
    Args:
        payload: Execution payload dictionary
        
    Returns:
        SHA256 hash of the payload as hexadecimal string
    
    Example:
        >>> payload1 = {"b": 2, "a": 1}
        >>> payload2 = {"a": 1, "b": 2}
        >>> generate_payload_hash(payload1) == generate_payload_hash(payload2)
        True
    """
    # Normalize payload first (handles nested structures)
    normalized = _normalize_for_hashing(payload)
    
    # Convert to JSON with sorted keys (lexicographic order)
    # This ensures consistent serialization regardless of insertion order
    payload_str = json.dumps(normalized, sort_keys=True, default=json_serial)
    
    # Generate SHA256 hash
    payload_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
    
    return payload_hash


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

