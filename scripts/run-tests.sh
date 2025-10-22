#!/bin/bash
# Script to run integration tests for AURA Processing Engine

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${GREEN}=== AURA Processing Engine - Integration Tests ===${NC}\n"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker is not running. Please start Docker first.${NC}"
    exit 1
fi

# Check if virtual environment is activated
if [ -z "$VIRTUAL_ENV" ]; then
    echo -e "${YELLOW}Warning: Virtual environment is not activated.${NC}"
    echo "Activating virtual environment..."
    source .venv/bin/activate
fi

# Check if docker-compose services are running
echo -e "${YELLOW}Checking Docker services...${NC}"
if ! docker-compose ps | grep -q "Up"; then
    echo -e "${YELLOW}Docker services are not running. Starting services...${NC}"
    docker-compose up -d

    echo -e "${YELLOW}Waiting for services to be ready (30 seconds)...${NC}"
    sleep 30
else
    echo -e "${GREEN}Docker services are already running.${NC}"
fi

# Display service status
echo -e "\n${GREEN}Service Status:${NC}"
docker-compose ps

# Wait a bit more to ensure all services are fully ready
echo -e "\n${YELLOW}Waiting for services to stabilize...${NC}"
sleep 5

# Run the tests
echo -e "\n${GREEN}Running integration tests...${NC}\n"
pytest tests/integration/test_services.py -v -s --tb=short

# Check test result
if [ $? -eq 0 ]; then
    echo -e "\n${GREEN}✓ All tests passed successfully!${NC}"
else
    echo -e "\n${RED}✗ Some tests failed. Check the output above.${NC}"
    exit 1
fi

