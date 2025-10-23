# AURA Processing Engine

A comprehensive underwriting processing engine that handles document processing, external integrations, factor extraction, and intelligent decision making.

## Overview

The AURA Processing Engine is part of the larger AURA Underwriting System, focusing on Team 3's responsibilities:
- Processor execution framework
- External API integrations (CLEAR, Experian, Equifax, etc.)
- Factor extraction and calculation
- Smart re-processing logic
- Error handling and retry mechanisms

## Architecture

This project uses a monolithic architecture with clear module boundaries:

```
processor/
├── src/aura/              # Main application code
│   ├── processing_engine/ # Core processing logic (Team 3)
│   ├── shared/           # Shared infrastructure
│   └── ...
├── tests/                # Test suite
├── scripts/              # Utility scripts
└── docker-compose.yml    # Development environment
```

## Prerequisites

- **Python 3.11+**
- **Docker & Docker Compose**
- **PostgreSQL 16** (via Docker)
- **Redis 7** (via Docker)

## 📚 Documentation

Comprehensive documentation is available in the [`docs/`](docs/) directory:

- **[FILTRATION.md](docs/FILTRATION.md)** - Filtration service guide (logging, testing, verification)
- **[API_WORKFLOWS.md](docs/API_WORKFLOWS.md)** - API endpoints and workflow execution
- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Service architecture and design

## Quick Start

### 1. Clone and Setup

```bash
# Clone the repository
git clone <repository-url>
cd processor

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy the example configuration
cp config.env.example .env

# Edit .env with your settings (optional for local development)
nano .env
```

### 3. Start Services

```bash
# Start all Docker services
docker-compose up -d

# Check service status
docker-compose ps

# View logs
docker-compose logs -f
```

### 4. Run Tests

```bash
# Run integration tests
./scripts/run-tests.sh

# Or run tests manually
pytest tests/integration/test_services.py -v
```

## Docker Services

The `docker-compose.yml` file includes the following services:

### PostgreSQL (Port 5432)
- **Purpose**: Operational database for underwriting data
- **Database**: `aura_underwriting`
- **User**: `aura_user`
- **Password**: `aura_password`
- **Features**: Complete schema with seed data

### BigQuery Emulator (Ports 9050, 9060)
- **Purpose**: Data warehouse emulation for analytics
- **Project**: `aura-project`
- **Dataset**: `underwriting_data`
- **Image**: `ghcr.io/goccy/bigquery-emulator`

### Google Cloud Storage Emulator (Port 4443)
- **Purpose**: Document storage emulation
- **Image**: `fsouza/fake-gcs-server`
- **Endpoint**: `http://localhost:4443`

### Pub/Sub Emulator (Port 8085)
- **Purpose**: Event messaging and async processing
- **Project**: `aura-project`
- **Image**: Google Cloud CLI with emulators

### Redis (Port 6379)
- **Purpose**: Caching layer for factors and session data
- **Image**: `redis:7-alpine`
- **Persistence**: Enabled with AOF

## Database Schema

The PostgreSQL database includes the following main table groups:

### 1. Identity & Auth
- `organization` - Multi-tenant organizations
- `account` - User accounts with Firebase integration
- `role` / `permission` - RBAC system
- `account_role` / `role_permission` - Permission mappings

### 2. Core Underwriting
- `underwriting` - Main underwriting records
- `merchant_address` - Business addresses
- `owner` / `owner_address` - Beneficial owners
- `document` / `document_revision` - Document management

### 3. Processing
- `organization_processors` - Processor entitlements
- `underwriting_processors` - Per-underwriting processor config
- `processor_executions` - Execution tracking

### 4. Factors
- `factor` - Atomic factor storage
- `factor_snapshot` - Point-in-time factor snapshots

### 5. Rules & Scoring
- `precheck_rule` - Business validation rules
- `precheck_evaluation` - Rule evaluation results
- `scorecard_config` - Scoring configurations
- `underwriting_score` - Score results

### 6. Decisions
- `suggestion` - AI-generated suggestions
- `decision` - Final human decisions

## Testing

### Integration Tests

The integration test suite validates all Docker services:

```bash
# Run all integration tests
pytest tests/integration/ -v

# Run specific test class
pytest tests/integration/test_services.py::TestPostgreSQL -v

# Run with coverage
pytest tests/integration/ --cov=src --cov-report=html
```

### Test Coverage

- **PostgreSQL**: Connection, schema validation, CRUD operations
- **BigQuery**: Connection, dataset/table creation
- **GCS**: Bucket operations, file upload/download
- **Pub/Sub**: Topic/subscription creation, message publishing
- **Redis**: Connection, key operations, hash operations, TTL

## Development Workflow

### 1. Start Development Environment

```bash
# Start all services
docker-compose up -d

# Watch logs
docker-compose logs -f
```

### 2. Make Changes

```bash
# Activate virtual environment
source .venv/bin/activate

# Make your changes in src/

# Run tests
pytest tests/
```

### 3. Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Add new table"

# Apply migrations
alembic upgrade head

# Rollback
alembic downgrade -1
```

### 4. Stop Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (clean slate)
docker-compose down -v
```

## Useful Commands

### Docker Management

```bash
# View service logs
docker-compose logs -f [service_name]

# Restart a service
docker-compose restart [service_name]

# Execute command in container
docker-compose exec postgres psql -U aura_user -d aura_underwriting

# View resource usage
docker stats
```

### Database Operations

```bash
# Connect to PostgreSQL
docker-compose exec postgres psql -U aura_user -d aura_underwriting

# Run SQL script
docker-compose exec -T postgres psql -U aura_user -d aura_underwriting < script.sql

# Backup database
docker-compose exec -T postgres pg_dump -U aura_user aura_underwriting > backup.sql

# Restore database
docker-compose exec -T postgres psql -U aura_user -d aura_underwriting < backup.sql
```

### Redis Operations

```bash
# Connect to Redis CLI
docker-compose exec redis redis-cli

# Monitor Redis commands
docker-compose exec redis redis-cli monitor

# Get Redis info
docker-compose exec redis redis-cli info
```

## Environment Variables

Key environment variables (see `config.env.example`):

| Variable | Description | Default |
|----------|-------------|---------|
| `POSTGRES_HOST` | PostgreSQL host | `localhost` |
| `POSTGRES_PORT` | PostgreSQL port | `5432` |
| `POSTGRES_DB` | Database name | `aura_underwriting` |
| `BIGQUERY_EMULATOR_HOST` | BigQuery emulator endpoint | `localhost:9060` |
| `STORAGE_EMULATOR_HOST` | GCS emulator endpoint | `http://localhost:4443` |
| `PUBSUB_EMULATOR_HOST` | Pub/Sub emulator endpoint | `localhost:8085` |
| `REDIS_HOST` | Redis host | `localhost` |
| `REDIS_PORT` | Redis port | `6379` |

## Troubleshooting

### Services Won't Start

```bash
# Check if ports are already in use
lsof -i :5432  # PostgreSQL
lsof -i :6379  # Redis
lsof -i :4443  # GCS

# Kill processes using the ports or change ports in docker-compose.yml
```

### Database Connection Issues

```bash
# Check PostgreSQL is ready
docker-compose exec postgres pg_isready -U aura_user

# Check logs
docker-compose logs postgres

# Restart PostgreSQL
docker-compose restart postgres
```

### Test Failures

```bash
# Ensure all services are healthy
docker-compose ps

# Wait for services to be ready
sleep 30 && pytest tests/integration/

# Check individual service health
docker-compose exec postgres pg_isready
docker-compose exec redis redis-cli ping
```

### Clear All Data

```bash
# Stop and remove all volumes
docker-compose down -v

# Restart fresh
docker-compose up -d

# Wait for initialization
sleep 30
```

## Project Structure

```
processor/
├── docker-compose.yml          # Docker services configuration
├── requirements.txt            # Python dependencies
├── pytest.ini                  # Pytest configuration
├── config.env.example          # Environment variable template
├── README.md                   # This file
├── scripts/
│   ├── init-db.sql            # PostgreSQL schema initialization
│   ├── run-tests.sh           # Test runner script
│   └── bigquery-init/         # BigQuery initialization scripts
├── tests/
│   ├── __init__.py
│   └── integration/
│       ├── __init__.py
│       └── test_services.py   # Service integration tests
└── src/
    └── aura/
        ├── processing_engine/ # Processing engine implementation (TODO)
        └── shared/           # Shared utilities (TODO)
```

## Next Steps

1. **Implement Processor Framework**: Create base processor classes
2. **Add External Integrations**: Implement API clients for CLEAR, Experian, etc.
3. **Build Factor Extraction**: Develop factor calculation logic
4. **Create Orchestration**: Implement parallel processor execution
5. **Add Smart Re-processing**: Build selective re-processing logic

## Contributing

1. Create a feature branch
2. Make your changes
3. Add tests
4. Run the test suite
5. Submit a pull request

## License

[Your License Here]

## Support

For issues and questions, please contact the development team.

