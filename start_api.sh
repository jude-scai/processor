#!/bin/bash

# Start AURA API Server

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                      AURA API Server                                 ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Activate virtual environment
source .venv/bin/activate

# Load environment variables from .env file if it exists
if [ -f .env ]; then
    echo "Loading environment variables from .env file..."
    export $(grep -v '^#' .env | xargs)
fi

# Set default PostgreSQL password if not set
export PGPASSWORD=${POSTGRES_PASSWORD:-aura_password}

# Check if PostgreSQL is running
echo "Checking PostgreSQL connection..."
if psql -h localhost -U aura_user -d aura_underwriting -c "SELECT 1" > /dev/null 2>&1; then
    echo "✅ PostgreSQL is running"
else
    echo "❌ PostgreSQL connection failed"
    echo ""
    echo "Please start PostgreSQL:"
    echo "  docker compose up -d postgres"
    echo ""
    echo "OR if using Docker, stop system PostgreSQL:"
    echo "  sudo systemctl stop postgresql"
    echo ""
    exit 1
fi

echo ""
echo "Starting API Server..."
echo ""
echo "Server will be available at:"
echo "  - API Root:    http://localhost:8000"
echo "  - Swagger UI:  http://localhost:8000/docs"
echo "  - ReDoc:       http://localhost:8000/redoc"
echo ""
echo "Press Ctrl+C to stop"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

# Start the server
python api.py

