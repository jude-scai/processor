"""
View Test Workflow Execution

Display test_workflow table data in a readable format for debugging.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent / "src"))

import psycopg2
from psycopg2.extras import RealDictCursor
import json

def view_workflow_stages(underwriting_id: str = None):
    """View workflow execution stages."""
    
    # Connect to database
    conn = psycopg2.connect(
        host="localhost",
        port=5432,
        database="aura_underwriting",
        user="aura_user",
        password="aura_password",
        cursor_factory=RealDictCursor
    )
    
    cursor = conn.cursor()
    
    # Query test_workflow
    if underwriting_id:
        query = """
            SELECT 
                id,
                underwriting_id,
                workflow_name,
                stage,
                payload,
                payload_hash,
                output,
                status,
                error_message,
                execution_time_ms,
                metadata,
                created_at
            FROM test_workflow
            WHERE underwriting_id = %s
            ORDER BY created_at ASC
        """
        cursor.execute(query, (underwriting_id,))
    else:
        query = """
            SELECT 
                id,
                underwriting_id,
                workflow_name,
                stage,
                payload,
                payload_hash,
                output,
                status,
                error_message,
                execution_time_ms,
                metadata,
                created_at
            FROM test_workflow
            ORDER BY created_at DESC
            LIMIT 20
        """
        cursor.execute(query)
    
    records = cursor.fetchall()
    
    cursor.close()
    conn.close()
    
    if not records:
        print("No workflow stages found")
        return
    
    print("=" * 80)
    print("TEST WORKFLOW EXECUTION STAGES")
    print("=" * 80)
    print()
    
    current_workflow = None
    
    for idx, record in enumerate(records, 1):
        # Print workflow header when it changes
        if record['workflow_name'] != current_workflow:
            if current_workflow is not None:
                print()
            current_workflow = record['workflow_name']
            print(f"{'═'*80}")
            print(f"{record['workflow_name']} - Underwriting: {record['underwriting_id']}")
            print(f"{'═'*80}")
            print()
        
        # Print stage details
        status_icon = "✅" if record['status'] == 'completed' else "❌" if record['status'] == 'failed' else "▶️"
        print(f"{status_icon} Stage: {record['stage'].upper()}")
        print(f"   Status: {record['status']}")
        print(f"   Time: {record['execution_time_ms']}ms" if record['execution_time_ms'] else "   Time: N/A")
        print(f"   Hash: {record['payload_hash']}")
        print(f"   Timestamp: {record['created_at']}")
        
        # Payload
        print(f"   Payload:")
        payload_str = json.dumps(record['payload'], indent=6)
        for line in payload_str.split('\n'):
            print(f"     {line}")
        
        # Output
        if record['output']:
            print(f"   Output:")
            output_str = json.dumps(record['output'], indent=6)
            for line in output_str.split('\n'):
                print(f"     {line}")
        
        # Metadata
        if record['metadata']:
            print(f"   Metadata:")
            metadata_str = json.dumps(record['metadata'], indent=6)
            for line in metadata_str.split('\n'):
                print(f"     {line}")
        
        # Error
        if record['error_message']:
            print(f"   ❌ Error: {record['error_message']}")
        
        print()
    
    print("=" * 80)
    print(f"Total stages: {len(records)}")
    print("=" * 80)

if __name__ == "__main__":
    import sys
    
    underwriting_id = sys.argv[1] if len(sys.argv) > 1 else None
    
    if underwriting_id:
        print(f"Viewing workflow stages for underwriting: {underwriting_id}")
        print()
    else:
        print("Viewing recent workflow stages (all underwritings)")
        print()
    
    view_workflow_stages(underwriting_id)

