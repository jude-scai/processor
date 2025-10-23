"""
Payload Formatting Utilities

Functions for transforming underwriting data into execution payloads.
"""

from typing import Any

from ..models import ProcessorType


def format_payload_list(
    processor_type: ProcessorType,
    processor_triggers: dict[str, list[str]],
    underwriting_data: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Format underwriting data into list of payloads for execution.
    
    Implementation varies based on processor type:
    - APPLICATION: Single payload with application form fields
    - STIPULATION: Single payload with all matching document revisions
    - DOCUMENT: One payload per matching document revision
    
    Args:
        processor_type: Type of processor (APPLICATION/STIPULATION/DOCUMENT)
        processor_triggers: Trigger configuration from processor
        underwriting_data: Complete underwriting data including merchant and owners
        
    Returns:
        List of payload dictionaries, or empty list if no triggers matched
    """
    if processor_type == ProcessorType.APPLICATION:
        return _format_application_payload(processor_triggers, underwriting_data)
    elif processor_type == ProcessorType.STIPULATION:
        return _format_stipulation_payload(processor_triggers, underwriting_data)
    elif processor_type == ProcessorType.DOCUMENT:
        return _format_document_payload(processor_triggers, underwriting_data)
    else:
        return []   


def _format_application_payload(
    processor_triggers: dict[str, list[str]],
    underwriting_data: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Format payload for APPLICATION type processor.
    
    Args:
        processor_triggers: Trigger configuration
        underwriting_data: Underwriting data with merchant info
        
    Returns:
        List containing single payload with application form, or empty if no data
    """
    # Get trigger fields from PROCESSOR_TRIGGERS
    trigger_fields = processor_triggers.get('application_form', [])
    
    # Build application form from underwriting merchant fields
    application_form = {}
    merchant = underwriting_data.get('merchant', {})
    
    # Map merchant fields to dot notation
    field_mapping = {
        'name': 'merchant.name',
        'ein': 'merchant.ein',
        'industry': 'merchant.industry',
        'email': 'merchant.email',
        'phone': 'merchant.phone',
        'website': 'merchant.website',
        'entity_type': 'merchant.entity_type',
        'incorporation_date': 'merchant.incorporation_date',
        'state_of_incorporation': 'merchant.state_of_incorporation',
    }
    
    for field, dot_key in field_mapping.items():
        value = merchant.get(field)
        if value is not None:
            application_form[dot_key] = value
    
    # Check if all trigger fields are null
    has_data = any(application_form.get(field) is not None for field in trigger_fields)
    
    if not has_data:
        return []
    
    # Return single payload with application form and owners
    return [{
        "application_form": application_form,
        "owners_list": underwriting_data.get('owners', [])
    }]


def _format_stipulation_payload(
    processor_triggers: dict[str, list[str]],
    underwriting_data: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Format payload for STIPULATION type processor.
    
    Groups all documents of the same stipulation type into a single payload.
    
    Args:
        processor_triggers: Trigger configuration
        underwriting_data: Underwriting data with documents
        
    Returns:
        List containing single payload with all revision IDs, or empty if no documents
    """
    # Get stipulation type from PROCESSOR_TRIGGERS
    trigger_docs = processor_triggers.get('documents_list', [])
    
    if not trigger_docs:
        return []
    
    stipulation_type = trigger_docs[0]  # e.g., 's_bank_statement'
    
    # Filter documents by stipulation type
    # Note: underwriting_data doesn't have documents yet - need to query separately
    # For now, return empty (will be enhanced when document integration is added)
    return []


def _format_document_payload(
    processor_triggers: dict[str, list[str]],
    underwriting_data: dict[str, Any]
) -> list[dict[str, Any]]:
    """
    Format payload for DOCUMENT type processor.
    
    Creates one payload per document revision.
    
    Args:
        processor_triggers: Trigger configuration
        underwriting_data: Underwriting data with documents
        
    Returns:
        List of payloads (one per document revision), or empty if no documents
    """
    # Get stipulation type from PROCESSOR_TRIGGERS
    trigger_docs = processor_triggers.get('documents_list', [])
    
    if not trigger_docs:
        return []
    
    # Filter documents and create one payload per document
    # Note: underwriting_data doesn't have documents yet - need to query separately
    # For now, return empty (will be enhanced when document integration is added)
    return []

