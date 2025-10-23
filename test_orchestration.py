"""
Test Orchestration Service - Workflow 1

Tests the orchestration service with Workflow 1 (Automatic Execution).
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))
sys.path.insert(0, str(Path(__file__).parent / "tests" / "unit" / "processing_engine"))

import psycopg2
from psycopg2.extras import RealDictCursor
from aura.processing_engine.orchestration_service import create_orchestration_service
from processors.application_processor import ApplicationProcessor

def test_workflow1():
    """Test Workflow 1 with orchestration service."""
    
    print("=" * 70)
    print("TESTING ORCHESTRATION SERVICE - WORKFLOW 1")
    print("=" * 70)
    print()
    
    # Connect to database
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="aura_underwriting",
        user="aura_user",
        password="aura_password",
        cursor_factory=RealDictCursor
    )
    
    # Create orchestration service
    orchestrator = create_orchestration_service(conn)
    
    # Register test processor (must match processor name in database)
    orchestrator.register_processor(
        processor_name="p_application",
        processor_class=ApplicationProcessor
    )
    
    print("✅ Orchestration service created")
    print("✅ ApplicationProcessor registered (p_application)")
    print()
    
    # Get existing underwriting ID
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM underwriting LIMIT 1")
    result = cursor.fetchone()
    
    if not result:
        print("❌ No underwriting found in database")
        print("   Please create an underwriting first")
        cursor.close()
        conn.close()
        return
    
    underwriting_id = result['id']
    cursor.close()
    
    print(f"Testing with underwriting: {underwriting_id}")
    print()
    
    # Execute Workflow 1
    print("Executing Workflow 1...")
    print("=" * 70)
    
    result = orchestrator.handle_workflow1(underwriting_id=underwriting_id)
    
    # Print results
    print("\n" + "=" * 70)
    print("WORKFLOW 1 RESULTS")
    print("=" * 70)
    print(f"Success: {result['success']}")
    print(f"Processors selected: {result['processors_selected']}")
    print(f"Executions run: {result['executions_run']}")
    print(f"Executions failed: {result['executions_failed']}")
    print(f"Processors consolidated: {result['processors_consolidated']}")
    
    if result['processors_selected'] == 0:
        print()
        print("ℹ️  No processors were selected.")
        print("   This is expected if:")
        print("   - No processors are purchased/enabled for this underwriting")
        print("   - No processors have auto=true")
        print("   - No processor triggers matched the available data")
    
    conn.close()
    print()
    print("=" * 70)

if __name__ == "__main__":
    test_workflow1()

