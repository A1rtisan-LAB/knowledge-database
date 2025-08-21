# 🏠 Local Deployment Guide (M1 Mac)

## 📦 Overview

This guide explains how to deploy the Knowledge Database in a production environment on M1 MacBook Pro.

## 🔧 Prerequisites

- Docker Desktop for Mac (M1/Apple Silicon)
- Minimum 8GB RAM allocation (recommended: 6GB for Docker)
- 10GB+ disk space
- Git

## 🚀 Quick Start

```bash
# 1. Clone repository
git clone <repository-url>
cd knowledge-database

# 2. Set up environment variables
cp .env.template .env.production
# Edit .env.production file to set required values

# 3. Run deployment
chmod +x scripts/deploy-local.sh
./scripts/deploy-local.sh

# Or use the start script with options
chmod +x scripts/start-local.sh
./scripts/start-local.sh           # Foreground mode
./scripts/start-local.sh --background  # Background mode
```

### Script Options

The `start-local.sh` script supports several options:

```bash
# Start in foreground (default)
./scripts/start-local.sh

# Start in background mode
./scripts/start-local.sh --background
# - Returns control to shell immediately
# - Logs are saved to logs/uvicorn.log
# - Perfect for development workflow

# Monitor background logs
tail -f logs/uvicorn.log

# Stop background services
docker-compose down
```

## 🎯 Running Modes

### Foreground Mode (Default)
- Application runs in current terminal
- Logs displayed in console
- Terminal remains occupied
- Use Ctrl+C to stop

### Background Mode
- Application runs in background
- Terminal control returned immediately
- Logs saved to `logs/uvicorn.log`
- Perfect for development and testing

```bash
# Start in background
./scripts/start-local.sh --background

# Check if running
docker-compose ps

# Monitor logs
tail -f logs/uvicorn.log

# Stop services
docker-compose down
```

## 📝 Detailed Configuration

### 1. Environment Variables Setup

Set the following variables in `.env.production`:

```env
# Security
SECRET_KEY=your-secret-key-here  # Generate strong secret key

# Database
DB_USER=kb_user
DB_PASSWORD=strong-password-here

# Redis
REDIS_PASSWORD=redis-password-here

# OpenSearch
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=opensearch-password
```

### 2. Docker Compose Configuration

Main services in `docker-compose.prod.yml`:

- **PostgreSQL**: Main database (port 5432)
- **Redis**: Caching layer (port 6379)
- **OpenSearch**: Search engine (port 9200)
- **Application**: FastAPI app (port 8000)
- **Nginx**: Reverse proxy (port 80/443)

### 3. Deployment Script Options

```bash
# Full deployment (default)
./scripts/deploy-local.sh

# App-only redeploy
./scripts/deploy-local.sh --app-only

# With database backup
./scripts/deploy-local.sh --with-backup

# Development mode (verbose logging)
./scripts/deploy-local.sh --debug
```

## 📈 Monitoring

### Service Status Check

```bash
# All services status
docker-compose -f docker-compose.prod.yml ps

# Health check
curl http://localhost:8000/health

# View logs
docker-compose -f docker-compose.prod.yml logs -f app
```

### Prometheus + Grafana (Optional)

```bash
# Start monitoring stack
docker-compose -f docker-compose.monitoring.yml up -d

# Access Grafana: http://localhost:3000
# Default credentials: admin/admin
```

## 🗓️ Backup and Recovery

### Backup

```bash
# Full backup
./scripts/backup-local.sh

# Database only backup
./scripts/backup-local.sh --db-only

# Backup location: ./backups/
```

### Recovery

```bash
# Restore from latest backup
./scripts/restore-local.sh

# Restore from specific backup file
./scripts/restore-local.sh --file backups/backup-20250821.tar.gz
```

## 🔄 Updates

```bash
# 1. Update code
git pull origin main

# 2. Rebuild images
docker build -f Dockerfile.prod -t knowledge-database:latest .

# 3. Restart services (zero-downtime)
docker-compose -f docker-compose.prod.yml up -d --no-deps app

# 4. Run migrations
docker exec kb-app-prod alembic upgrade head
```

## 🎯 Performance Optimization

### M1 Mac Optimization

1. **Docker Desktop Settings**:
   - Settings → Resources → Advanced
   - CPUs: 4
   - Memory: 6GB
   - Swap: 2GB
   - Disk image size: 60GB

2. **Platform Specification**:
   Specify `platform: linux/arm64` for all images

3. **Memory Allocation**:
   - PostgreSQL: 2GB
   - OpenSearch: 2GB (Java heap)
   - Redis: 512MB
   - App: 1.5GB

### Caching Strategy

- Redis TTL: 3600 seconds (1 hour)
- Static files: Nginx caching
- Database: Connection pooling

## 🔒 Security

### Firewall Configuration

```bash
# macOS firewall rules
sudo pfctl -e
sudo pfctl -f /etc/pf.conf
```

### SSL/TLS (Optional)

```bash
# Let's Encrypt certificate
./scripts/setup-ssl.sh

# Self-signed certificate (development)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout configs/nginx/ssl/private.key \
  -out configs/nginx/ssl/certificate.crt
```

## 🆘 Troubleshooting

### Common Issues

1. **Port Conflicts**:
   ```bash
   # Check ports in use
   lsof -i :5432
   lsof -i :6379
   lsof -i :9200
   ```

2. **Memory Issues**:
   ```bash
   # Clean Docker resources
   docker system prune -a
   docker volume prune
   ```

3. **Service Start Failure**:
   ```bash
   # Restart individual service
   docker-compose -f docker-compose.prod.yml restart <service-name>
   ```

### Log Locations

- Application (foreground): Console output
- Application (background): `./logs/uvicorn.log`
- PostgreSQL: `docker logs kb-postgres-prod`
- OpenSearch: `docker logs kb-opensearch-prod`
- Redis: `docker logs kb-redis-prod`

### Log Management

#### Background Mode Logs
When running with `--background` flag:

```bash
# View real-time logs
tail -f logs/uvicorn.log

# View last 100 lines
tail -n 100 logs/uvicorn.log

# Search for errors
grep ERROR logs/uvicorn.log

# View with timestamps
less logs/uvicorn.log
```

#### Clean Output Features
The start script provides clean, organized output by:
- Suppressing Docker Compose warnings
- Converting Alembic migration messages to info level
- Organizing logs in structured format
- Providing clear status messages
- Nginx: `./logs/nginx/`

## 📞 Support

For issues:

1. Check logs: `./logs/` directory
2. Health check: `http://localhost:8000/health`
3. Documentation: `docs/` directory
4. GitHub Issues

---

**Last Updated**: 2025-08-21