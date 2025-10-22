#!/usr/bin/env python3
"""
Initialize BigQuery schema for AURA Processing Engine against the emulator.

Notes:
- The emulator reliably supports JSON REST operations and client.create_* calls.
- Executing DDL (CREATE TABLE ...) via SQL can be flaky; so we use client.create_table.
"""
import os
import sys
from pathlib import Path
from google.cloud import bigquery
from google.auth.credentials import AnonymousCredentials

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def init_bigquery_schema():
    """Initialize BigQuery schema using client.create_table (fast and reliable on emulator)."""

    project_id = os.getenv("BIGQUERY_PROJECT", "aura-project")
    dataset_id = os.getenv("BIGQUERY_DATASET", "underwriting_data")
    emulator_host = os.getenv("BIGQUERY_EMULATOR_HOST", "localhost:9050")  # REST port

    # Ensure emulator host env var is set for client
    os.environ["BIGQUERY_EMULATOR_HOST"] = emulator_host

    print(f"🔧 Initializing BigQuery schema…", flush=True)
    print(f"   Project: {project_id}", flush=True)
    print(f"   Dataset: {dataset_id}", flush=True)
    print(f"   Emulator: {emulator_host}", flush=True)

    client = bigquery.Client(
        project=project_id,
        credentials=AnonymousCredentials(),
        client_options={"api_endpoint": f"http://{emulator_host}"}
    )

    # Create dataset
    full_dataset_id = f"{project_id}.{dataset_id}"
    dataset = bigquery.Dataset(full_dataset_id)
    dataset.location = "US"
    client.create_dataset(dataset, exists_ok=True)
    print(f"✅ Dataset ready: {dataset_id}", flush=True)

    # Minimal table set needed for dev/testing; the full schema.sql is large
    tables: list[tuple[str, list[bigquery.SchemaField]]] = [
        (
            "underwriting",
            [
                bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("organization_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("serial_number", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("merchant_name", "STRING"),
                bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("updated_at", "TIMESTAMP", mode="REQUIRED"),
                bigquery.SchemaField("created_by", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("updated_by", "STRING", mode="REQUIRED"),
            ],
        ),
        (
            "document",
            [
                bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("underwriting_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("stipulation_type", "STRING"),
                bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            ],
        ),
        (
            "processor_executions",
            [
                bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("underwriting_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("processor", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("payload", "JSON"),
                bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            ],
        ),
        (
            "factor",
            [
                bigquery.SchemaField("id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("underwriting_id", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("factor_key", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("value", "JSON", mode="REQUIRED"),
                bigquery.SchemaField("status", "STRING", mode="REQUIRED"),
                bigquery.SchemaField("created_at", "TIMESTAMP", mode="REQUIRED"),
            ],
        ),
    ]

    created = 0
    for name, schema in tables:
        table_ref = f"{full_dataset_id}.{name}"
        table = bigquery.Table(table_ref, schema=schema)
        client.create_table(table, exists_ok=True)
        created += 1
        print(f"   • ✅ {name}", flush=True)

    print(f"\n🎉 Schema initialization complete ({created} tables created/verified)", flush=True)

    # Verify list
    tables_list = list(client.list_tables(full_dataset_id))
    print(f"📊 Tables now present ({len(tables_list)}):", flush=True)
    for t in tables_list:
        print(f"   • {t.table_id}", flush=True)

    return True

if __name__ == "__main__":
    try:
        success = init_bigquery_schema()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Schema initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

