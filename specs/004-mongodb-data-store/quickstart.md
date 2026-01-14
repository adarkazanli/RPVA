# Quickstart: MongoDB Data Store for Voice Agent

**Date**: 2026-01-14
**Feature**: [spec.md](spec.md)

## Prerequisites

- Docker 20.10+ installed
- Python 3.11+
- ~5GB available disk space
- 8GB RAM (Raspberry Pi 4 or higher)

## Setup

### 1. Start MongoDB Container

Create `docker/docker-compose.yml`:

```yaml
version: '3.9'

services:
  mongodb:
    image: arm64v8/mongo:4.4.18
    container_name: ara_mongodb
    ports:
      - "27017:27017"
    volumes:
      - mongodb_data:/data/db
    command:
      - "--wiredTigerCacheSizeGB=4"
    deploy:
      resources:
        limits:
          memory: 4500M
    healthcheck:
      test: echo 'db.runCommand("ping").ok' | mongo localhost:27017/test --quiet
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 40s
    restart: unless-stopped

volumes:
  mongodb_data:
```

Start the container:

```bash
cd docker
docker-compose up -d
```

Verify it's running:

```bash
docker ps
# Should show ara_mongodb as "healthy"
```

### 2. Install Python Dependencies

```bash
pip install pymongo>=4.6.0
```

Or add to `requirements.txt`:

```
pymongo>=4.6.0
```

### 3. Connect from Python

```python
from pymongo import MongoClient

# Connect to local MongoDB
client = MongoClient(
    'mongodb://localhost:27017',
    serverSelectionTimeoutMS=5000
)

# Verify connection
client.admin.command('ping')
print("Connected to MongoDB!")

# Get the ara database
db = client['ara']
```

## Basic Usage

### Save an Interaction

```python
from datetime import datetime

interaction = {
    "session_id": "550e8400-e29b-41d4-a716-446655440000",
    "timestamp": datetime.utcnow(),
    "device_id": "pi-living-room",
    "input": {
        "transcript": "I'm going to take a shower",
        "confidence": 0.95
    },
    "intent": {
        "type": "activity_log",
        "confidence": 0.88
    },
    "response": {
        "text": "Got it, starting your shower timer.",
        "source": "local_llm"
    }
}

result = db.interactions.insert_one(interaction)
print(f"Saved interaction: {result.inserted_id}")
```

### Query Events Around a Time

```python
from datetime import datetime, timedelta

# Find events around 10:30 AM today
target_time = datetime.now().replace(hour=10, minute=30, second=0)
window = timedelta(minutes=15)

events = db.events.find({
    "timestamp": {
        "$gte": target_time - window,
        "$lte": target_time + window
    }
}).sort("timestamp", 1)

for event in events:
    print(f"{event['timestamp']}: {event['context']}")
```

### Calculate Duration Between Events

```python
# Get duration of an activity
activity = db.activities.find_one({"name": "shower", "status": "completed"})

if activity:
    duration_ms = activity['duration_ms']
    minutes = duration_ms // 60000
    seconds = (duration_ms % 60000) // 1000
    print(f"Shower duration: {minutes} minutes, {seconds} seconds")
```

## Development Workflow

### Run Tests

```bash
# Unit tests
PYTHONPATH=src pytest tests/unit/test_storage*.py -v

# Integration tests (requires MongoDB running)
PYTHONPATH=src pytest tests/integration/test_mongodb*.py -v

# Benchmarks
PYTHONPATH=src pytest tests/benchmark/test_query_latency.py -v
```

### Stop MongoDB

```bash
cd docker
docker-compose down

# To also remove data volume:
docker-compose down -v
```

## Troubleshooting

### Connection Refused

```
pymongo.errors.ServerSelectionTimeoutError: localhost:27017
```

**Solution**: Ensure MongoDB container is running:
```bash
docker ps | grep ara_mongodb
docker-compose up -d
```

### Memory Issues on Pi

If MongoDB is killed by OOM:

1. Check WiredTiger cache size is set:
   ```bash
   docker logs ara_mongodb | grep wiredTiger
   ```

2. Reduce cache if needed:
   ```yaml
   command:
     - "--wiredTigerCacheSizeGB=2"
   ```

### Slow Queries

Add indexes for your query patterns:

```python
# Time-based index
db.events.create_index([("timestamp", -1)])

# Compound index for filtered queries
db.events.create_index([("type", 1), ("timestamp", -1)])
```

## Next Steps

1. Review [data-model.md](data-model.md) for schema details
2. Review [contracts/storage.py](contracts/storage.py) for interface definitions
3. Run `/speckit.tasks` to generate implementation tasks
