# API for AURA Processing Engine

A standalone FastAPI application for testing the Application Processor and Underwriting Repository integration.

## Quick Start

### 1. Ensure Services Are Running

```bash
# Make sure PostgreSQL is running
docker compose up -d postgres

# Or check if system PostgreSQL is stopped (if using Docker)
sudo systemctl stop postgresql
```

### 2. Start the Test API

```bash
# Activate virtual environment
source .venv/bin/activate

# Run the API
python api.py

# OR use uvicorn directly
uvicorn api:app --reload --port 8000
```

### 3. Access the API

- **API Root**: http://localhost:8000
- **Interactive Docs (Swagger)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc

## API Endpoints

### Core Endpoints

#### `POST /process`
Execute Application Processor and save to database.

**Request Body:**
```json
{
  "underwriting_id": "uw_001",
  "merchant_name": "ABC Tech Inc",
  "merchant_ein": "12-3456789",
  "merchant_industry": "Technology",
  "merchant_state": "CA",
  "merchant_entity_type": "LLC",
  "owners": [
    {
      "owner_id": "owner_001",
      "first_name": "John",
      "last_name": "Doe",
      "email": "john@example.com",
      "ownership_percent": 60.0,
      "primary_owner": true
    }
  ],
  "user_id": "test_user"
}
```

**Response:**
```json
{
  "success": true,
  "execution_id": "exec_uw_001_p_test_application",
  "processor_output": {
    "application_form": {...},
    "owners_list": [...]
  },
  "save_result": {
    "application_form_saved": true,
    "owners_operations": {
      "inserted": [],
      "updated": ["owner_001"],
      "removed": []
    }
  },
  "message": "Application processed and saved successfully"
}
```

#### `GET /owners/{underwriting_id}`
Get owners for an underwriting.

**Example:**
```bash
curl http://localhost:8000/owners/uw_001
```

#### `GET /application-form/{underwriting_id}`
Get application form data for an underwriting.

#### `POST /restore-owner/{owner_id}`
Restore a soft-deleted owner.

#### `GET /health`
Health check endpoint.

### Test Scenario Endpoints

Pre-configured test scenarios to demonstrate different use cases:

#### `POST /test/scenario-1-new-owners`
**Scenario:** Create new underwriting with 2 new owners
- Creates `uw_test_001`
- Adds John Doe (60%) and Jane Smith (40%)

#### `POST /test/scenario-2-update-owners`
**Scenario:** Update existing owners
- Updates John and Jane's ownership percentages
- Updates John's email

#### `POST /test/scenario-3-remove-owner`
**Scenario:** Reduce owners from 2 to 1
- Keeps John (100%)
- Removes Jane (soft delete)

#### `POST /test/scenario-4-add-new-owner`
**Scenario:** Add new owner while keeping existing
- Keeps John (60%)
- Adds Bob Johnson (40%)

## Testing Workflow

### Using Swagger UI (Recommended)

1. Open http://localhost:8000/docs
2. Click on **POST /test/scenario-1-new-owners**
3. Click "Try it out"
4. Click "Execute"
5. Check the response
6. Try **GET /owners/uw_test_001** to see the owners
7. Try other scenarios in order

### Using curl

```bash
# Test Scenario 1: Create with 2 owners
curl -X POST http://localhost:8000/test/scenario-1-new-owners | jq

# Check owners
curl http://localhost:8000/owners/uw_test_001 | jq

# Test Scenario 3: Remove one owner (2 → 1)
curl -X POST http://localhost:8000/test/scenario-3-remove-owner | jq

# Check owners again (Jane should be disabled)
curl http://localhost:8000/owners/uw_test_001?enabled_only=false | jq

# Restore Jane
curl -X POST http://localhost:8000/restore-owner/owner_002 | jq

# Check owners again
curl http://localhost:8000/owners/uw_test_001 | jq
```

### Using Python

```python
import requests

# Test Scenario 1
response = requests.post("http://localhost:8000/test/scenario-1-new-owners")
print(response.json())

# Get owners
response = requests.get("http://localhost:8000/owners/uw_test_001")
print(response.json())
```

## Test Scenarios Explained

### Scenario 1: New Owners (First Submission)
```
Input:  2 new owners (no owner_id)
Result: 2 owners INSERTed
```

### Scenario 2: Update Owners
```
Input:  2 existing owners (with owner_id)
Result: 2 owners UPDATEd
```

### Scenario 3: Remove Owner (2 → 1)
```
Input:  1 owner (John only)
Result: 
  - John: UPDATEd (ownership 60% → 100%)
  - Jane: SOFT DELETEd (enabled = false)
```

### Scenario 4: Add New Owner
```
Input:  1 existing (John) + 1 new (Bob)
Result:
  - John: UPDATEd
  - Bob: INSERTed
```

## Verifying Results in Database

```bash
# Connect to PostgreSQL
docker exec -it aura-postgres psql -U aura_user -d aura_underwriting

# Check owners
SELECT owner_id, first_name, last_name, ownership_percent, enabled 
FROM owners 
WHERE underwriting_id = 'uw_test_001';

# Check application form
SELECT id, application_form 
FROM underwritings 
WHERE id = 'uw_test_001';
```

## Troubleshooting

### Port Already in Use
```bash
# Kill process on port 8000
lsof -ti:8000 | xargs kill -9
```

### Database Connection Error
```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Check connection
psql -h localhost -U aura_user -d aura_underwriting

# If using system PostgreSQL, stop it
sudo systemctl stop postgresql
```

### Import Errors
```bash
# Make sure you're in the virtual environment
source .venv/bin/activate

# Check imports work
python -c "from aura.processing_engine.repositories import UnderwritingRepository; print('OK')"
```

## What This Tests

✅ **Application Processor Execution**
- Input validation
- Data transformation
- Output structuring

✅ **Underwriting Repository**
- Application form persistence
- Owner INSERT/UPDATE/DELETE logic
- Soft delete functionality
- Transaction handling

✅ **Owner Matching**
- New owners (owner_id = null)
- Existing owners (owner_id present)
- Removed owners (missing from input)

✅ **Complete Integration**
- Processor → Repository → Database
- End-to-end data flow
- Real database operations

## Notes

- This is a **test API only** - not for production use
- No authentication/authorization
- Direct database access (no ORM)
- Simplified error handling
- For testing and demonstration purposes only

