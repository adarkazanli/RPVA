# Research: MongoDB Data Store for Voice Agent

**Date**: 2026-01-14
**Feature**: [spec.md](spec.md)

## Research Summary

This document consolidates research findings for implementing MongoDB-based persistent storage with time-based queries and semantic event pairing for the Ara voice assistant on Raspberry Pi 4.

---

## 1. MongoDB on Raspberry Pi 4

### MongoDB Version Selection

**Decision**: MongoDB 4.4.18 via `arm64v8/mongo:4.4.18` Docker image

**Rationale**:
- MongoDB 5.0+ requires ARMv8.2-A architecture, but Pi 4 uses ARMv8.0-A (Cortex-A72)
- MongoDB 4.4.18 is the latest version with official ARM64 support for Pi 4
- Official Docker Hub image with proven stability on Pi hardware

**Alternatives Considered**:
- MongoDB 5.0+ with unofficial binaries: Lack official support
- Self-compiled MongoDB: 6+ hours compilation time
- MongoDB 4.2.x: Older, reduced features

### Memory Configuration

**Decision**: WiredTiger cache 4GB, Docker limit 4.5GB

**Rationale**:
- MongoDB ignores Docker memory limits without explicit WiredTiger configuration
- 4GB cache on 8GB Pi leaves 4GB for OS + application
- Prevents swap thrashing and OOM conditions

**Configuration**:
```yaml
command:
  - "--wiredTigerCacheSizeGB=4"
deploy:
  resources:
    limits:
      memory: 4500M
```

---

## 2. Python MongoDB Driver

### Driver Selection

**Decision**: PyMongo with async support (not Motor)

**Rationale**:
- Motor is deprecated (May 2025), end-of-life May 2027
- PyMongo Async API is the official replacement
- Avoids Motor's thread pool overhead

**Alternatives Considered**:
- Motor: Deprecated, unnecessary overhead
- MongoEngine ODM: Adds abstraction layer, slower

### Connection Pooling

**Decision**: Single MongoClient instance with 10-50 connection pool

**Rationale**:
- MongoClient is thread-safe with built-in pooling
- Pi 4 can handle 10-50 connections comfortably
- Single instance prevents resource leaks

**Configuration**:
```python
client = MongoClient(
    'mongodb://localhost:27017',
    maxPoolSize=50,
    minPoolSize=10,
    connectTimeoutMS=5000,
    serverSelectionTimeoutMS=5000
)
```

### Error Handling

**Decision**: Exponential backoff with max 5 retries

**Rationale**:
- Network issues common on Pi (WiFi drops)
- Backoff prevents server overload during transient failures
- 5 retries = ~31 second retry window (1+2+4+8+16)

---

## 3. Docker Compose Configuration

### Recommended Configuration

**Decision**: Version 3.9+ with named volumes, health checks, resource limits

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

**Key Points**:
- Named volumes for data persistence across restarts
- 40s startup grace period for slow Pi boot
- `unless-stopped` restart policy for crash recovery

---

## 4. Time-Based Query Indexing

### Index Strategy

**Decision**: Compound index on (metaField, timestamp DESC)

**Rationale**:
- Supports both equality filtering and time range queries
- Descending timestamp enables efficient "latest event" queries
- O(log n) query performance vs O(n) full scan

**Index Configuration**:
```python
# Primary time index
db.events.create_index([("timestamp", -1)])

# Compound index for filtered queries
db.events.create_index([("event_type", 1), ("timestamp", -1)])

# For activity pairing queries
db.events.create_index([("context", 1), ("timestamp", -1)])
```

### Range Query Pattern

**Decision**: Use `$gte` and `$lt` with compound indexes

**Example - Events around a time point**:
```python
target_time = datetime.now()
window = timedelta(minutes=15)

events = db.events.find({
    "timestamp": {
        "$gte": target_time - window,
        "$lte": target_time + window
    }
}).sort("timestamp", 1)
```

### Duration Calculation

**Decision**: MongoDB aggregation with `$subtract` operator

**Example - Time between events**:
```python
pipeline = [
    {"$match": {"session_id": session_id}},
    {"$sort": {"timestamp": 1}},
    {"$group": {
        "_id": "$activity_type",
        "start": {"$first": "$timestamp"},
        "end": {"$last": "$timestamp"}
    }},
    {"$project": {
        "duration_ms": {"$subtract": ["$end", "$start"]}
    }}
]
```

---

## 5. Semantic Similarity for Event Pairing

### Model Selection

**Decision**: fastText word vectors (primary approach)

**Rationale**:
- 33-50MB memory footprint (optimizable to 15MB)
- <1ms per comparison on Pi 4
- Handles synonyms via subword embeddings
- Fully offline, no cloud dependency

**Alternatives Considered**:
- Sentence Transformers: 500MB+, too slow (~1s per comparison)
- ONNX models: 100-200MB, viable upgrade path
- BM25/TF-IDF: Lexical only, misses semantic relationships

### Event Pairing Strategy

**Decision**: Multi-factor scoring approach

| Factor | Weight | Purpose |
|--------|--------|---------|
| Semantic similarity | 40% | Word vector cosine similarity |
| Entity matching | 30% | Shared people, places, objects |
| Temporal proximity | 20% | Time ordering and gap size |
| Category alignment | 10% | Same activity type |

**Scoring Formula**:
```python
def pair_score(event1, event2):
    semantic = cosine_similarity(embed(event1.context), embed(event2.context))
    entity = entity_overlap(event1.entities, event2.entities)
    temporal = temporal_score(event1.timestamp, event2.timestamp)
    category = 1.0 if event1.type == event2.type else 0.5

    return (0.4 * semantic + 0.3 * entity + 0.2 * temporal + 0.1 * category)
```

**Pairing Rules**:
- Activity start/end: 4-hour time window, >0.7 score threshold
- Task chains: 30-minute max gap, >0.65 threshold
- Wrong temporal order (end before start): score = 0

### Synonym Handling

**Decision**: fastText subword + rule-based synonym groups

**Built-in Synonyms** (JSON file):
```json
{
  "gym": ["workout", "training", "exercise", "fitness"],
  "shower": ["bath", "washing up"],
  "cooking": ["making food", "preparing meal", "baking"]
}
```

**Rationale**:
- fastText handles unseen words via character n-grams
- Rule-based groups catch domain-specific aliases
- User can add personal activity names

---

## 6. Performance Benchmarks (Expected)

| Operation | Target | Method |
|-----------|--------|--------|
| Single event insert | <50ms | Indexed collection |
| Time range query (24h) | <500ms | Compound index |
| Duration calculation | <200ms | Aggregation pipeline |
| Event pairing | <100ms | fastText + scoring |
| Full interaction save | <100ms | Single document |

---

## 7. Technology Stack Summary

| Component | Technology | Version | Memory |
|-----------|------------|---------|--------|
| Database | MongoDB | 4.4.18 | 4.5GB limit |
| Python driver | PyMongo | Latest | Minimal |
| Container | Docker | 20.10+ | N/A |
| Semantic model | fastText | cc.en.300 | 33-50MB |
| Scoring | Custom | N/A | <1MB |

---

## References

- [MongoDB ARM64 Docker Image](https://hub.docker.com/r/arm64v8/mongo/)
- [PyMongo Async Migration Guide](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/reference/migration/)
- [Time Series Collections Best Practices](https://www.mongodb.com/docs/manual/core/timeseries/timeseries-best-practices/)
- [fastText Pre-trained Vectors](https://fasttext.cc/docs/en/english-vectors.html)
- [MongoDB Connection Pooling](https://www.mongodb.com/docs/languages/python/pymongo-driver/current/connect/connection-options/connection-pools/)
