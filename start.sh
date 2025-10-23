#!/bin/bash

# Start AURA Services (API + Subscriber)

echo "╔══════════════════════════════════════════════════════════════════════╗"
echo "║                      AURA Services Startup                           ║"
echo "╚══════════════════════════════════════════════════════════════════════╝"
echo ""

# Activate virtual environment
if [ -d ".venv" ]; then
    echo "Activating virtual environment..."
    source .venv/bin/activate
else
    echo "❌ Virtual environment not found. Please run: python -m venv .venv"
    exit 1
fi

# Set PYTHONPATH to include src directory
export PYTHONPATH="$PWD/src:$PYTHONPATH"

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

# Check if Pub/Sub emulator is running
echo "Checking Pub/Sub emulator..."
if curl -s http://localhost:8085 > /dev/null 2>&1; then
    echo "✅ Pub/Sub emulator is running"
else
    echo "❌ Pub/Sub emulator not running"
    echo ""
    echo "Please start Pub/Sub emulator:"
    echo "  docker compose up -d pubsub-emulator"
    echo ""
    exit 1
fi

echo ""
echo "═══════════════════════════════════════════════════════════════════════"
echo "Starting services..."
echo "═══════════════════════════════════════════════════════════════════════"
echo ""

# Create log directory
mkdir -p logs

# Start API server in background
echo "🚀 Starting API Server..."
python api.py 2>&1 | tee logs/api.log &
API_PID=$!
echo "   API Server PID: $API_PID"

# Wait for API to be ready
echo "   Waiting for API to start..."
API_STARTED=false
for i in {1..20}; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        API_STARTED=true
        break
    fi
    sleep 0.5
done

if [ "$API_STARTED" = false ]; then
    echo ""
    echo "❌ API failed to start!"
    echo "   Check logs: tail -f logs/api.log"
    kill $API_PID 2>/dev/null
    exit 1
fi

echo "   ✅ API is ready"
echo "   API Root:       http://localhost:8000"
echo "   Swagger UI:     http://localhost:8000/docs"
echo "   ReDoc:          http://localhost:8000/redoc"
echo ""

# Start Pub/Sub subscriber with auto-reload in background
echo "🎧 Starting Pub/Sub Subscriber (auto-reload)..."
python subscriber.py --reload 2>&1 | tee logs/subscriber.log &
SUBSCRIBER_PID=$!
echo "   Subscriber PID: $SUBSCRIBER_PID"

# Wait for subscriber to confirm it's listening
echo "   Waiting for subscriber to start..."
SUBSCRIBER_STARTED=false
for i in {1..10}; do
    if grep -q "🎧 Subscriber is running" logs/subscriber.log 2>/dev/null; then
        SUBSCRIBER_STARTED=true
        break
    fi
    sleep 0.5
done

if [ "$SUBSCRIBER_STARTED" = false ]; then
    echo ""
    echo "❌ Subscriber failed to start!"
    echo "   Check logs: tail -f logs/subscriber.log"
    kill $API_PID $SUBSCRIBER_PID 2>/dev/null
    exit 1
fi

echo "   ✅ Subscriber is listening"
echo ""

echo "═══════════════════════════════════════════════════════════════════════"
echo "✅ All services started!"
echo "═══════════════════════════════════════════════════════════════════════"
echo ""
echo "Logs:"
echo "  - API:        tail -f logs/api.log"
echo "  - Subscriber: tail -f logs/subscriber.log"
echo ""
echo "To stop services:"
echo "  - Press Ctrl+C"
echo "  - Or run: kill $API_PID $SUBSCRIBER_PID"
echo ""
echo "Press Ctrl+C to stop all services..."
echo ""

# Function to cleanup on exit
cleanup() {
    echo ""
    echo "⏹️  Stopping services..."
    kill $API_PID $SUBSCRIBER_PID 2>/dev/null
    echo "✓ Services stopped"
    exit 0
}

# Trap Ctrl+C and call cleanup
trap cleanup INT TERM

# Wait for processes
wait

