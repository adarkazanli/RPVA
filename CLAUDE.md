# 11-RPVA Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-01-12

## Active Technologies
- Python 3.11+ + Ollama (existing), standard library (json, pathlib, datetime) (002-personality-timers)
- JSON file (`~/.ara/reminders.json`) (002-personality-timers)
- Python 3.11+ + Ollama (existing), standard library (threading, time, datetime) (003-timer-countdown)
- JSON file (`~/.ara/user_profile.json`) for user profile (003-timer-countdown)
- Python 3.11+ + pymongo (MongoDB driver), motor (async driver), Docker (004-mongodb-data-store)
- MongoDB 7.0+ (local Docker container) (004-mongodb-data-store)

- Python 3.11+ (001-ara-voice-assistant)

## Project Structure

```text
src/
tests/
```

## Commands

cd src [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] pytest [ONLY COMMANDS FOR ACTIVE TECHNOLOGIES][ONLY COMMANDS FOR ACTIVE TECHNOLOGIES] ruff check .

## Code Style

Python 3.11+: Follow standard conventions

## Recent Changes
- 004-mongodb-data-store: Added Python 3.11+ + pymongo (MongoDB driver), motor (async driver), Docker
- 003-timer-countdown: Added Python 3.11+ + Ollama (existing), standard library (threading, time, datetime)
- 002-personality-timers: Added Python 3.11+ + Ollama (existing), standard library (json, pathlib, datetime)


<!-- MANUAL ADDITIONS START -->
## MongoDB Setup

Start MongoDB using Docker Compose:
```bash
docker compose -f docker/docker-compose.yml up -d
```

Stop MongoDB:
```bash
docker compose -f docker/docker-compose.yml down
```

The MongoDB container uses:
- Port: 27017
- Volume: `mongodb_data` for persistence
- Image: `arm64v8/mongo:4.4.18` (Raspberry Pi 4 compatible)

## Time Query Voice Commands

Duration queries:
- "How long was I in the shower?"
- "How long did my workout take?"

Activity search:
- "What was I doing around 10 AM?"
- "What happened between 9 and noon?"
- "What did I do yesterday?"
- "When did I last mention groceries?"

Event logging:
- "I'm going to the gym" (starts tracking)
- "I'm done with my workout" (ends tracking)
- "Remember to call mom tomorrow" (saves note)
<!-- MANUAL ADDITIONS END -->
