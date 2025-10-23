"""
AURA API - Underwriting System

Endpoints to list and retrieve underwritings with merchant, owners, and addresses.
Run with: uvicorn api:app --reload --port 8000
"""

import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import psycopg2
from psycopg2.extras import RealDictCursor
from google.cloud import pubsub_v1
from google.auth.credentials import AnonymousCredentials
import json
import os

from aura.processing_engine.repositories import UnderwritingRepository

# Pub/Sub configuration
os.environ["PUBSUB_EMULATOR_HOST"] = "localhost:8085"
PUBSUB_PROJECT = "aura-project"

# ============================================================================
# FastAPI App Setup
# ============================================================================

app = FastAPI(
    title="AURA API",
    description="API for listing underwritings with merchant details, owners, and addresses",
    version="1.0.0"
)

# ============================================================================
# Database Connection
# ============================================================================

def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="aura_underwriting",
        user="aura_user",
        password="aura_password",
        cursor_factory=RealDictCursor
    )

# ============================================================================
# Pub/Sub Publisher
# ============================================================================

def get_publisher():
    """Get Pub/Sub publisher client."""
    return pubsub_v1.PublisherClient(credentials=AnonymousCredentials())

def publish_message(topic_name: str, data: dict) -> str:
    """
    Publish a message to Pub/Sub topic.
    
    Args:
        topic_name: Topic name (e.g., 'underwriting.updated')
        data: Message data dictionary
        
    Returns:
        Message ID
    """
    publisher = get_publisher()
    topic_path = f"projects/{PUBSUB_PROJECT}/topics/{topic_name}"
    
    # Ensure topic exists
    try:
        publisher.get_topic(request={"topic": topic_path})
    except:
        # Create topic if it doesn't exist
        publisher.create_topic(request={"name": topic_path})
    
    # Publish message
    message_data = json.dumps(data).encode("utf-8")
    future = publisher.publish(topic_path, message_data)
    message_id = future.result()
    
    return message_id

# ============================================================================
# Request Models
# ============================================================================

class TriggerWorkflow1Request(BaseModel):
    """Request to trigger Workflow 1 (underwriting.updated)."""
    underwriting_id: str

class TriggerWorkflow2Request(BaseModel):
    """Request to trigger Workflow 2 (underwriting.processor.execute)."""
    underwriting_processor_id: str
    execution_id: str | None = None
    duplicate: bool = False

class TriggerWorkflow3Request(BaseModel):
    """Request to trigger Workflow 3 (underwriting.processor.consolidation)."""
    underwriting_processor_id: str

class TriggerWorkflow4Request(BaseModel):
    """Request to trigger Workflow 4 (underwriting.execution.activate)."""
    execution_id: str

class TriggerWorkflow5Request(BaseModel):
    """Request to trigger Workflow 5 (underwriting.execution.disable)."""
    execution_id: str

# ============================================================================
# API Endpoints
# ============================================================================

@app.get("/")
def root():
    """API information."""
    return {
        "message": "AURA API",
        "version": "1.0.0",
        "endpoints": {
            "GET /underwritings": "List all underwritings",
            "GET /underwritings/{id}": "Get single underwriting",
            "POST /trigger/workflow1": "Trigger Workflow 1 (underwriting.updated)",
            "POST /trigger/workflow2": "Trigger Workflow 2 (processor.execute)",
            "POST /trigger/workflow3": "Trigger Workflow 3 (processor.consolidation)",
            "POST /trigger/workflow4": "Trigger Workflow 4 (execution.activate)",
            "POST /trigger/workflow5": "Trigger Workflow 5 (execution.disable)",
            "GET /health": "Health check"
        }
    }

@app.get("/health")
def health_check():
    """Health check endpoint."""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}

@app.get("/underwritings")
def list_underwritings():
    """List all underwritings with merchant details, owners, and addresses."""
    try:
        conn = get_db_connection()
        repo = UnderwritingRepository(conn)
        
        # Use repository method
        underwritings = repo.list_all_underwritings()
        
        conn.close()
        
        return {
            "count": len(underwritings),
            "underwritings": underwritings
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/underwritings/{underwriting_id}")
def get_underwriting(underwriting_id: str):
    """Get a single underwriting with complete details. Returns 404 if not found."""
    try:
        conn = get_db_connection()
        repo = UnderwritingRepository(conn)
        
        # Use repository method
        underwriting = repo.get_underwriting_with_details(underwriting_id)
        
        conn.close()
        
        if not underwriting:
            raise HTTPException(status_code=404, detail="Underwriting not found")
        
        return underwriting
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Workflow Trigger Endpoints
# ============================================================================

@app.post("/trigger/workflow1")
def trigger_workflow1(request: TriggerWorkflow1Request):
    """Trigger Workflow 1 - Automatic processor execution (underwriting.updated)."""
    try:
        message_id = publish_message(
            topic_name="underwriting.updated",
            data={"underwriting_id": request.underwriting_id}
        )
        
        return {
            "success": True,
            "workflow": "Workflow 1 - Automatic Execution",
            "topic": "underwriting.updated",
            "message_id": message_id,
            "payload": {"underwriting_id": request.underwriting_id}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger/workflow2")
def trigger_workflow2(request: TriggerWorkflow2Request):
    """Trigger Workflow 2 - Manual processor execution (underwriting.processor.execute)."""
    try:
        payload = {"underwriting_processor_id": request.underwriting_processor_id}
        
        if request.execution_id:
            payload["execution_id"] = request.execution_id
        
        if request.duplicate:
            payload["duplicate"] = request.duplicate
        
        message_id = publish_message(
            topic_name="underwriting.processor.execute",
            data=payload
        )
        
        return {
            "success": True,
            "workflow": "Workflow 2 - Manual Execution",
            "topic": "underwriting.processor.execute",
            "message_id": message_id,
            "payload": payload
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger/workflow3")
def trigger_workflow3(request: TriggerWorkflow3Request):
    """Trigger Workflow 3 - Processor consolidation (underwriting.processor.consolidation)."""
    try:
        message_id = publish_message(
            topic_name="underwriting.processor.consolidation",
            data={"underwriting_processor_id": request.underwriting_processor_id}
        )
        
        return {
            "success": True,
            "workflow": "Workflow 3 - Consolidation Only",
            "topic": "underwriting.processor.consolidation",
            "message_id": message_id,
            "payload": {"underwriting_processor_id": request.underwriting_processor_id}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger/workflow4")
def trigger_workflow4(request: TriggerWorkflow4Request):
    """Trigger Workflow 4 - Execution activation (underwriting.execution.activate)."""
    try:
        message_id = publish_message(
            topic_name="underwriting.execution.activate",
            data={"execution_id": request.execution_id}
        )
        
        return {
            "success": True,
            "workflow": "Workflow 4 - Execution Activation",
            "topic": "underwriting.execution.activate",
            "message_id": message_id,
            "payload": {"execution_id": request.execution_id}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/trigger/workflow5")
def trigger_workflow5(request: TriggerWorkflow5Request):
    """Trigger Workflow 5 - Execution deactivation (underwriting.execution.disable)."""
    try:
        message_id = publish_message(
            topic_name="underwriting.execution.disable",
            data={"execution_id": request.execution_id}
        )
        
        return {
            "success": True,
            "workflow": "Workflow 5 - Execution Deactivation",
            "topic": "underwriting.execution.disable",
            "message_id": message_id,
            "payload": {"execution_id": request.execution_id}
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# Run Instructions
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("""
    ╔══════════════════════════════════════════════════════════════════════╗
    ║                      AURA API Server                                 ║
    ╚══════════════════════════════════════════════════════════════════════╝
    
    Server starting on: http://localhost:8000
    API Documentation: http://localhost:8000/docs
    Alternative docs: http://localhost:8000/redoc
    
    Endpoints:
    -----------
    GET  /                            API information
    GET  /health                      Health check
    GET  /underwritings                List all underwritings
    GET  /underwritings/{id}           Get single underwriting
    
    Quick Test:
    -----------
    curl http://localhost:8000/health
    curl http://localhost:8000/underwritings
    
    """)
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
