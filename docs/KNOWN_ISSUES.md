# 🐛 Known Issues

## Current Issues

### 1. Python Dependency Conflicts
**Issue**: Version conflict between `httpx` and `googletrans` packages
- **Status**: ⚠️ Workaround Available
- **Impact**: Cannot use Google Translate API with strict httpx version
- **Workaround**: 
  - Use flexible version: `httpx>=0.13.3`
  - Or use `requirements-core.txt` for minimal setup
  - Comment out `googletrans` if not needed
- **Tracking**: [Issue #001]

### 2. Missing Dependencies in requirements.txt
**Issue**: `bleach` and `itsdangerous` modules not included
- **Status**: ✅ Fixed
- **Impact**: Application fails to start with ModuleNotFoundError
- **Solution**: Added to requirements.txt:
  ```
  bleach==6.1.0
  itsdangerous==2.2.0
  ```
- **Tracking**: [Issue #002]

### 3. pgvector Extension Installation
**Issue**: PostgreSQL container doesn't auto-install pgvector extension
- **Status**: ✅ Fixed
- **Impact**: Database operations fail with "type vector does not exist"
- **Solution**: 
  - Created `migrations/init.sql` with extension setup
  - Added to docker-compose.yml volumes
  - Automated in `scripts/start-local.sh`
- **Tracking**: [Issue #003]

### 4. Port 8000 Conflicts
**Issue**: Port 8000 often already in use on developer machines
- **Status**: ⚠️ Workaround Available
- **Impact**: Application fails to start
- **Workaround**: 
  - Kill existing processes: `pkill -f uvicorn`
  - Or use different port: `--port 8001`
- **Tracking**: [Issue #004]

### 5. Docker Desktop on macOS
**Issue**: Docker daemon doesn't auto-start on macOS
- **Status**: ⚠️ Workaround Available
- **Impact**: All Docker commands fail
- **Workaround**: 
  - Manual start: `open -a Docker`
  - Automated in `scripts/start-local.sh`
- **Tracking**: [Issue #005]

### 6. M1 Mac Compatibility
**Issue**: Some Docker images not optimized for ARM64
- **Status**: ⚠️ Partial Fix
- **Impact**: Slower performance due to emulation
- **Solution**: 
  - Using ARM64-compatible images where available
  - pgvector/pgvector:pg16 supports ARM64
  - Enable Rosetta 2 in Docker Desktop for x86 emulation
- **Tracking**: [Issue #006]

### 7. Environment Variable Configuration
**Issue**: `.env` file not automatically created
- **Status**: ✅ Fixed
- **Impact**: Application fails with missing SECRET_KEY error
- **Solution**: 
  - Automated in `scripts/start-local.sh`
  - Copies from `.env.example` if missing
- **Tracking**: [Issue #007]

### 8. Alembic Migration Initialization
**Issue**: Alembic not initialized on fresh setup
- **Status**: ⚠️ Workaround Available
- **Impact**: Database migrations fail
- **Workaround**: 
  - Automated initialization in `scripts/start-local.sh`
  - Manual: `alembic init -t async migrations`
- **Tracking**: [Issue #008]

## Resolved Issues

### ✅ Requirements File Cleanup (v1.0.1)
- Removed duplicate entries
- Fixed version conflicts
- Created minimal `requirements-core.txt`
- **Resolution Date**: 2025-08-21

### ✅ Docker Compose Configuration (v1.0.1)
- Added pgvector initialization
- Fixed healthcheck configurations
- Added proper network setup
- **Resolution Date**: 2025-08-21

### ✅ Local Setup Automation (v1.0.1)
- Created `scripts/start-local.sh` for one-command setup
- Handles all common setup issues automatically
- **Resolution Date**: 2025-08-21

## Upcoming Fixes

### Version 1.1.0 (Planned)
1. Replace `googletrans` with `deep-translator` for better compatibility
2. Implement automatic port detection and allocation
3. Add Docker daemon status check to all scripts
4. Create platform-specific setup scripts (macOS, Linux, Windows)
5. Add automatic Alembic initialization to application startup

### Version 1.2.0 (Planned)
1. Full ARM64 optimization for all services
2. Kubernetes deployment configurations
3. Automated dependency resolution system
4. Enhanced error messages with fix suggestions

## Reporting New Issues

To report a new issue:
1. Check if it's already listed above
2. Search existing GitHub issues
3. Create new issue with:
   - Clear description
   - Steps to reproduce
   - Environment details (OS, Python version, Docker version)
   - Error messages/logs
   - Attempted solutions

## Quick Fixes Reference

```bash
# Dependency conflicts
pip install -r requirements-core.txt

# Port conflicts
pkill -f uvicorn

# Docker not running (macOS)
open -a Docker && sleep 30

# pgvector extension
docker exec knowledge-postgres psql -U postgres -d knowledge_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Missing .env
cp .env.example .env

# Full automated setup
./scripts/start-local.sh
```

## Version History

- **v1.0.1** (2025-08-21): Initial troubleshooting improvements
  - Added automated setup script
  - Fixed dependency conflicts
  - Improved Docker configuration
  - Added comprehensive troubleshooting documentation

- **v1.0.0** (2025-08-20): Initial release
  - Core functionality implemented
  - Basic Docker support
  - Initial documentation

---

**Last Updated**: 2025-08-21  
**Maintained By**: Development Team  
**Issue Tracker**: [GitHub Issues](https://github.com/your-org/knowledge-database/issues)