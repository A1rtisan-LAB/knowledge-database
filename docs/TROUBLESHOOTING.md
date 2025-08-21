# 🔧 Knowledge Database Troubleshooting Guide

## Table of Contents
1. [Common Issues](#common-issues)
2. [Installation Problems](#installation-problems)
3. [Runtime Errors](#runtime-errors)
4. [Performance Issues](#performance-issues)
5. [Database Problems](#database-problems)
6. [Search Issues](#search-issues)
7. [Authentication & Authorization](#authentication--authorization)
8. [Docker & Deployment](#docker--deployment)
9. [M1 Mac Specific Issues](#m1-mac-specific-issues)
10. [Emergency Procedures](#emergency-procedures)

## Common Issues

### Application Won't Start

#### Symptom
```
ERROR: Application failed to start
```

#### Diagnosis & Solution
```bash
# Check if all services are running
docker-compose ps

# Check application logs
docker logs kb-app-prod

# Common causes:
# 1. Database connection failed
psql -h localhost -U kb_user -d knowledge_db -c "SELECT 1"

# 2. Port already in use
lsof -i :8000
kill -9 <PID>

# 3. Environment variables missing
cat .env
# Ensure all required variables are set

# 4. Dependencies not installed
pip install -r requirements.txt
```

### Quick Local Setup Script

For quick local setup, use the automated script:
```bash
# Make script executable
chmod +x scripts/start-local.sh

# Run the script
./scripts/start-local.sh

# This script handles:
# - Docker daemon check and startup
# - Environment file creation
# - PostgreSQL extension setup
# - Dependency installation
# - Database migrations
# - Application startup
```

### Import Errors

#### Symptom
```python
ModuleNotFoundError: No module named 'app'
```

#### Solution
```bash
# Add project to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# Or in your virtual environment
pip install -e .

# Verify installation
python -c "import app; print(app.__file__)"
```

## Installation Problems

### Python Dependency Conflicts

#### Symptom
```
ERROR: Cannot install httpx==0.25.2 and googletrans 4.0.0-rc1 because these package versions have conflicting dependencies
```

#### Solution
```bash
# Use flexible version constraints
# Edit requirements.txt:
httpx>=0.13.3  # Instead of httpx==0.25.2

# Or use minimal requirements
pip install -r requirements-core.txt

# Comment out conflicting packages
# googletrans==4.0.0-rc1  # Conflicts with httpx
```

### Missing Python Modules

#### Symptom
```
ModuleNotFoundError: No module named 'bleach'
ModuleNotFoundError: No module named 'itsdangerous'
```

#### Solution
```bash
# Install missing packages
pip install bleach itsdangerous opensearch-py

# These are often missing from requirements.txt
# Add to requirements.txt:
bleach==6.1.0
itsdangerous==2.2.0
```

### Docker Compose Fails

#### Symptom
```
ERROR: Service 'opensearch' failed to build
```

#### Solution
```bash
# Clean Docker cache
docker system prune -a

# Rebuild with no cache
docker-compose build --no-cache

# If memory issues on M1 Mac
# Increase Docker Desktop memory to 6GB minimum
# Settings → Resources → Advanced → Memory: 6GB
```

### Docker Daemon Not Running

#### Symptom
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

#### Solution
```bash
# On macOS
open -a Docker

# Wait for Docker to start
sleep 30

# Verify Docker is running
docker info

# On Linux
sudo systemctl start docker
sudo systemctl enable docker
```

### PostgreSQL Connection Failed

#### Symptom
```
psycopg2.OperationalError: connection to server failed
```

#### Solution
```bash
# Check PostgreSQL is running
docker-compose ps postgres

# Test connection
docker exec -it kb-postgres-prod psql -U kb_user -d knowledge_db

# Check configuration
cat docker-compose.yml | grep -A 5 postgres

# Verify network
docker network ls
docker network inspect knowledge-database_default
```

### pgvector Extension Not Installed

#### Symptom
```
ERROR: type "vector" does not exist
```

#### Solution
```bash
# Install pgvector extension in PostgreSQL
docker exec knowledge-postgres psql -U postgres -d knowledge_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Also install uuid extension if needed
docker exec knowledge-postgres psql -U postgres -d knowledge_db -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"

# Or add to docker-compose.yml volumes:
volumes:
  - ./migrations/init.sql:/docker-entrypoint-initdb.d/init.sql

# Create migrations/init.sql with:
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### Port 8000 Already in Use

#### Symptom
```
[Errno 48] Address already in use
[Errno 98] Address already in use
```

#### Solution
```bash
# Find process using port 8000
lsof -i :8000

# Kill existing uvicorn processes
pkill -f uvicorn

# Or kill specific PID
kill -9 <PID>

# Use different port if needed
uvicorn app.main:app --port 8001
```

### Environment Variables Not Set

#### Symptom
```
ValueError: [SECRET_KEY] not found in environment
```

#### Solution
```bash
# Create .env from example
cp .env.example .env

# Generate secure SECRET_KEY
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Update .env file
SECRET_KEY=your_generated_secret_key_here

# Source environment variables
source .env
# Or use python-dotenv
```

### OpenSearch Won't Start

#### Symptom
```
OpenSearch container exits with code 137 (OOM)
```

#### Solution
```bash
# Increase memory limits
# Edit docker-compose.yml
services:
  opensearch:
    environment:
      - "OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g"
    mem_limit: 2g

# On host system, increase vm.max_map_count
sudo sysctl -w vm.max_map_count=262144

# Make permanent
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

## Runtime Errors

### Pydantic Validation Errors

#### Symptom
```python
pydantic.error_wrappers.ValidationError: 1 validation error for Settings
```

#### Solution
```python
# Check environment variables format
# .env file
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-minimum-32-chars

# For lists in environment variables
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

### JWT Token Errors

#### Symptom
```
jose.exceptions.JWTError: Invalid token
```

#### Solution
```python
# Verify SECRET_KEY is set
import os
print(os.getenv("SECRET_KEY"))

# Check token expiration
from datetime import datetime, timedelta
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# Verify token format
# Should be: Bearer <token>
headers = {"Authorization": "Bearer eyJ..."}

# Clear Redis cache if token issues persist
redis-cli FLUSHDB
```

## Performance Issues

### Slow API Response Times

#### Diagnosis
```bash
# Check resource usage
docker stats

# Monitor database queries
docker exec -it kb-postgres-prod psql -U kb_user -d knowledge_db
\x
SELECT query, calls, mean_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
```

#### Solutions
```python
# 1. Add database indexes
CREATE INDEX idx_items_created ON knowledge_items(created_at DESC);
CREATE INDEX idx_items_category ON knowledge_items(category_id);

# 2. Implement caching
from app.core.cache import cache

@cache(expire=300)
async def get_popular_items():
    # Expensive query cached for 5 minutes
    pass

# 3. Use pagination
@router.get("/items")
async def list_items(skip: int = 0, limit: int = 100):
    # Limit results
    pass

# 4. Optimize queries
# Use select_related for joins
items = db.query(Item).options(selectinload(Item.category)).all()
```

### High Memory Usage

#### Diagnosis
```bash
# Check memory usage by container
docker stats --no-stream

# Find memory leaks in Python
pip install memory_profiler
python -m memory_profiler app/main.py
```

#### Solutions
```bash
# 1. Limit worker connections
gunicorn app.main:app \
  --workers 2 \
  --worker-connections 100 \
  --max-requests 1000 \
  --max-requests-jitter 50

# 2. Clear caches periodically
redis-cli
> INFO memory
> FLUSHDB

# 3. Optimize Docker memory
docker update --memory="1g" --memory-swap="2g" kb-app-prod
```

## Database Problems

### Migration Failures

#### Symptom
```
alembic.util.exc.CommandError: Can't locate revision identified by 'head'
```

#### Solution
```bash
# Check migration history
alembic history

# Stamp current database state
alembic stamp head

# Create fresh migrations
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

# Rollback if needed
alembic downgrade -1
```

### Connection Pool Exhausted

#### Symptom
```
sqlalchemy.exc.TimeoutError: QueuePool limit exceeded
```

#### Solution
```python
# Increase pool size in database.py
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)

# Monitor connections
SELECT count(*) FROM pg_stat_activity;

# Kill idle connections
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND state_change < now() - interval '10 minutes';
```

## Search Issues

### OpenSearch Index Missing

#### Symptom
```
opensearchpy.exceptions.NotFoundError: index not found
```

#### Solution
```bash
# Create index
curl -X PUT "localhost:9200/knowledge_items" \
  -H 'Content-Type: application/json' \
  -d @configs/opensearch/index_mapping.json

# Reindex all data
docker exec -it kb-app-prod python scripts/reindex.py

# Check index health
curl -X GET "localhost:9200/_cat/indices?v"
```

### Korean Search Not Working

#### Symptom
Korean text returns no results

#### Solution
```json
// Update analyzer configuration
PUT /knowledge_items/_settings
{
  "analysis": {
    "analyzer": {
      "korean_analyzer": {
        "type": "custom",
        "tokenizer": "nori_tokenizer",
        "filter": ["nori_part_of_speech"]
      }
    }
  }
}

// Reindex with new analyzer
POST _reindex
{
  "source": {"index": "knowledge_items"},
  "dest": {"index": "knowledge_items_v2"}
}
```

## Authentication & Authorization

### Login Fails

#### Diagnosis
```python
# Check password hashing
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
print(pwd_context.hash("test_password"))

# Verify user exists
docker exec -it kb-postgres-prod psql -U kb_user -d knowledge_db
SELECT email, is_active FROM users WHERE email = 'user@example.com';
```

### Permission Denied

#### Solution
```python
# Check user role
SELECT role FROM users WHERE email = 'user@example.com';

# Update user role if needed
UPDATE users SET role = 'editor' WHERE email = 'user@example.com';

# Clear cache after role change
redis-cli DEL user_cache:user@example.com
```

## Docker & Deployment

### OpenSearch Dashboards Locale Error

#### Symptom
```
[I18n] A `locale` must be a non-empty string to add messages.
Version: 2.11.0
Build: 6665
Error: [I18n] A `locale` must be a non-empty string to add messages.
```

#### Cause
This error occurs when OpenSearch Dashboards cannot properly initialize the i18n (internationalization) system, often due to missing or misconfigured locale settings.

#### Solution
1. **Create a configuration file** for OpenSearch Dashboards:
```yaml
# opensearch-dashboards.yml
server.host: "0.0.0.0"
server.port: 5601

opensearch.hosts: ["http://opensearch:9200"]
opensearch.ssl.verificationMode: none

# Fix locale issue
i18n.locale: "en"

logging.dest: stdout
logging.verbose: false

map.includeOpenSearchMapsService: false
```

2. **Update docker-compose.yml** to use the configuration:
```yaml
opensearch-dashboards:
  image: opensearchproject/opensearch-dashboards:2.11.0
  container_name: knowledge-opensearch-dashboards
  ports:
    - "5601:5601"
  environment:
    OPENSEARCH_HOSTS: '["http://opensearch:9200"]'
    DISABLE_SECURITY_DASHBOARDS_PLUGIN: "true"
  volumes:
    - ./opensearch-dashboards.yml:/usr/share/opensearch-dashboards/config/opensearch_dashboards.yml
  depends_on:
    opensearch:
      condition: service_healthy
```

3. **Clear browser cache** and restart the container:
```bash
docker restart knowledge-opensearch-dashboards
# Clear browser cache (Ctrl+Shift+R or Cmd+Shift+R)
# Or try in incognito/private browsing mode
```

4. **Alternative: Use API directly** if UI issues persist:
```bash
# Check OpenSearch health
curl http://localhost:9200/_cluster/health?pretty

# List indices
curl http://localhost:9200/_cat/indices?v

# Search data
curl -X GET "localhost:9200/knowledge_items/_search?pretty"
```

### Container Keeps Restarting

#### Diagnosis
```bash
# Check container logs
docker logs --tail 50 kb-app-prod

# Check exit code
docker inspect kb-app-prod --format='{{.State.ExitCode}}'

# Common exit codes:
# 0 - Success
# 1 - General errors
# 125 - Docker daemon error
# 126 - Container command not executable
# 127 - Container command not found
# 137 - Out of memory (OOM)
# 139 - Segmentation fault
```

### Build Fails on M1 Mac

#### Solution
```dockerfile
# Specify platform in Dockerfile
FROM --platform=linux/arm64 python:3.11-slim

# Or in docker-compose.yml
services:
  app:
    platform: linux/arm64
    build:
      context: .
      dockerfile: Dockerfile
```

## M1 Mac Specific Issues

### Architecture Mismatch

#### Symptom
```
WARNING: The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8)
```

#### Solution
```bash
# Use ARM64 compatible images
docker pull --platform linux/arm64 postgres:15
docker pull --platform linux/arm64 redis:7-alpine
docker pull --platform linux/arm64 opensearchproject/opensearch:2.11.0

# Build with buildx for multi-arch
docker buildx build --platform linux/arm64,linux/amd64 -t myapp:latest .
```

### Rosetta 2 Performance Issues

#### Solution
```bash
# Enable Rosetta 2 in Docker Desktop
# Settings → Features in development → Use Rosetta for x86/amd64 emulation

# Or use native ARM images
# Update docker-compose.yml to use ARM-specific tags
image: postgres:15-alpine  # ARM64 compatible
```

## Emergency Procedures

### Complete System Recovery

```bash
#!/bin/bash
# emergency_recovery.sh

echo "Starting emergency recovery..."

# 1. Stop all services
docker-compose down

# 2. Backup current state
mkdir -p backups/emergency_$(date +%Y%m%d_%H%M%S)
docker exec kb-postgres-prod pg_dump -U kb_user knowledge_db > backups/emergency_$(date +%Y%m%d_%H%M%S)/database.sql

# 3. Clean up
docker system prune -f
docker volume prune -f

# 4. Restore from last known good backup
docker-compose up -d postgres
sleep 10
docker exec -i kb-postgres-prod psql -U kb_user knowledge_db < backups/last_known_good.sql

# 5. Start services one by one
docker-compose up -d redis
docker-compose up -d opensearch
sleep 30
docker-compose up -d app
docker-compose up -d nginx

# 6. Verify health
curl http://localhost:8000/health

echo "Recovery complete. Please verify system functionality."
```

### Data Corruption Recovery

```sql
-- Check for corruption
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- Rebuild corrupted indexes
REINDEX TABLE knowledge_items;
REINDEX DATABASE knowledge_db;

-- Vacuum and analyze
VACUUM FULL ANALYZE;
```

### Performance Emergency

```bash
# Quick performance fixes
# 1. Clear all caches
redis-cli FLUSHALL

# 2. Restart application with reduced workers
docker-compose scale app=1

# 3. Disable non-critical features
export DISABLE_ANALYTICS=true
export DISABLE_TRANSLATIONS=true

# 4. Increase timeouts temporarily
export REQUEST_TIMEOUT=60
export DATABASE_POOL_TIMEOUT=30

# 5. Monitor and gradually restore
docker stats --no-stream
```

## Getting Help

### Log Locations

#### Application Logs
**Foreground Mode**:
- Console output (visible in terminal)
- Use Ctrl+C to stop and see full log

**Background Mode**:
- Logs saved to: `logs/uvicorn.log`
- View logs: `tail -f logs/uvicorn.log`
- Check errors: `grep ERROR logs/uvicorn.log`
- Last 100 lines: `tail -n 100 logs/uvicorn.log`

#### Container Logs
- Application: `docker logs kb-app-prod`
- PostgreSQL: `docker logs kb-postgres-prod`
- OpenSearch: `docker logs kb-opensearch-prod`
- Redis: `docker logs kb-redis-prod`
- Nginx: `docker logs kb-nginx-prod`

#### Log Analysis Commands
```bash
# Search for specific error patterns
grep -i "connection refused" logs/uvicorn.log
grep -i "timeout" logs/uvicorn.log
grep -i "memory" logs/uvicorn.log

# Count error occurrences
grep -c ERROR logs/uvicorn.log

# View logs with timestamps
less logs/uvicorn.log

# Monitor multiple log files
tail -f logs/*.log
```

### Debug Mode

#### Enable Debug Logging
```bash
# For foreground mode
export LOG_LEVEL=DEBUG
export SQLALCHEMY_ECHO=true
./scripts/start-local.sh

# For background mode
export LOG_LEVEL=DEBUG
export SQLALCHEMY_ECHO=true
./scripts/start-local.sh --background
tail -f logs/uvicorn.log  # Monitor debug output
```

#### Clean Output Features
When using the start script:
- Docker Compose warnings are suppressed
- Alembic migration messages are formatted cleanly
- Logs are structured and organized
- Clear status indicators show service state

#### Troubleshooting Background Mode
```bash
# Check if services are running
docker-compose ps

# View background logs
tail -f logs/uvicorn.log

# Stop background services
docker-compose down

# Clean restart
docker-compose down
./scripts/start-local.sh --background
```

### Support Contacts
- **System Admin**: admin@your-domain.com
- **Dev Team**: dev-team@your-domain.com
- **Emergency**: +1-XXX-XXX-XXXX
- **Documentation**: https://docs.your-domain.com

---

**Version**: 1.0.0  
**Last Updated**: 2025-08-21  
**Emergency Hotline**: Call if production is down