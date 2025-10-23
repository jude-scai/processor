#!/usr/bin/env python3
"""Test ProcessorRepository methods"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from aura.processing_engine.repositories.processor_repository import ProcessorRepository

# Load environment
load_dotenv()

# Database connection
def get_db_connection():
    return psycopg2.connect(
        host="localhost",  # Always use localhost from host machine
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB", "aura_underwriting"),
        user=os.getenv("POSTGRES_USER", "aura_user"),
        password=os.getenv("POSTGRES_PASSWORD", "aura_password")
    )

def test_processor_repo():
    print("Testing ProcessorRepository...")
    
    conn = get_db_connection()
    repo = ProcessorRepository(conn)
    
    underwriting_id = "e1b38421-6157-41d3-bd13-f2c2f74771b3"
    
    print(f"\nGetting processors for underwriting: {underwriting_id}")
    processors = repo.get_underwriting_processors(
        underwriting_id=underwriting_id,
        enabled_only=True,
        auto_only=True
    )
    
    print(f"\nFound {len(processors)} processors:")
    for processor in processors:
        print(f"\nProcessor:")
        for key, value in processor.items():
            print(f"  {key}: {value}")
    
    conn.close()

if __name__ == "__main__":
    test_processor_repo()

