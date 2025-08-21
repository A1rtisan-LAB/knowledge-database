# Knowledge Database

![Build Status](https://img.shields.io/badge/build-passing-brightgreen)
![Coverage](https://img.shields.io/badge/coverage-84.9%25-yellow)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![Platform](https://img.shields.io/badge/platform-M1%20Mac%20%7C%20AWS-orange)

## Overview

Knowledge Database is an enterprise-grade knowledge management system built with FastAPI, designed to efficiently store, search, and manage organizational knowledge with advanced features including vector search, bilingual support (English/Korean), and AI-powered embeddings.

## Key Features

### Core Capabilities
- **Bilingual Support**: Full support for English and Korean content with automatic translation
- **Vector Search**: AI-powered semantic search using OpenSearch and embeddings
- **Real-time Caching**: Redis-based caching layer for optimized performance
- **Advanced Analytics**: Usage tracking, search patterns, and knowledge insights
- **Enterprise Security**: JWT authentication, role-based access control, input validation
- **Audit Logging**: Complete audit trail for compliance and security
- **RESTful API**: Well-documented API with OpenAPI/Swagger support

### Technical Highlights
- **Microservices Architecture**: Modular design with clear service boundaries
- **Async/Await**: Full asynchronous support for high concurrency
- **Type Safety**: Comprehensive type hints with Pydantic validation
- **Test Coverage**: 345+ tests with 84.9% code coverage
- **Production Ready**: Docker containerization with multi-environment support

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                         Client Layer                        │
│                    (Web, Mobile, API Clients)               │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                      API Gateway (Nginx)                    │
│                    Load Balancing & SSL/TLS                 │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    FastAPI Application                      │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               Middleware Layer                        │  │
│  │  (Rate Limiting, Logging, Input Validation, CORS)    │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  API Endpoints                        │  │
│  │  /auth  /knowledge  /search  /categories  /analytics │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 Service Layer                         │  │
│  │  Search Service, Embedding Service, Cache Service     │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼──────┐     ┌────────▼────────┐   ┌───────▼──────┐
│  PostgreSQL  │     │   OpenSearch    │   │    Redis     │
│   Database   │     │  Vector Search  │   │    Cache     │
└──────────────┘     └─────────────────┘   └──────────────┘
```

## Technology Stack

### Backend
- **Framework**: FastAPI 0.104.1
- **Language**: Python 3.11+
- **Server**: Uvicorn with async support

### Data Storage
- **Primary Database**: PostgreSQL 15 with pgvector extension
- **Search Engine**: OpenSearch 2.x for vector similarity search
- **Cache Layer**: Redis 7.x for session and query caching

### Infrastructure
- **Containerization**: Docker & Docker Compose
- **Cloud Platform**: AWS (ECS, RDS, ElastiCache, OpenSearch)
- **Local Development**: Optimized for M1 Mac (ARM64)

### Security & Authentication
- **Authentication**: JWT tokens with refresh mechanism
- **Encryption**: bcrypt for password hashing
- **Input Validation**: Pydantic schemas with sanitization
- **Rate Limiting**: Token bucket algorithm

### Testing & Quality
- **Unit Testing**: pytest with 84.9% coverage
- **Integration Testing**: Full API endpoint testing
- **Performance Testing**: Load testing with locust
- **Code Quality**: black, isort, flake8, mypy

## Installation

### Prerequisites

- Python 3.11 or higher
- Docker Desktop (for M1 Mac: ARM64 version)
- 8GB RAM minimum (6GB for Docker)
- 10GB available disk space

### Quick Start

```bash
# Clone the repository
git clone https://github.com/your-org/knowledge-database.git
cd knowledge-database

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.template .env
# Edit .env with your configuration

# Start services with Docker Compose
docker-compose up -d

# Run database migrations
alembic upgrade head

# Start the application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or use the convenience script
./scripts/start-local.sh           # Run in foreground
./scripts/start-local.sh --background  # Run in background (returns to shell)
```

### Running in Background Mode

The application supports background execution for development convenience:

```bash
# Start in background mode
./scripts/start-local.sh --background

# The application will:
# - Start all services in the background
# - Return control to your shell immediately  
# - Save logs to logs/uvicorn.log

# Monitor logs
tail -f logs/uvicorn.log

# Stop background services
docker-compose down
```

### Production Deployment (Local M1 Mac)

```bash
# Use the automated deployment script
chmod +x scripts/deploy-local.sh
./scripts/deploy-local.sh

# Or manually with production compose file
docker-compose -f docker-compose.prod.yml up -d

# Check service health
curl http://localhost:8000/health
```

### AWS Deployment

```bash
# Configure AWS credentials
aws configure

# Deploy infrastructure with Terraform
cd infrastructure/terraform
terraform init
terraform plan
terraform apply

# Deploy application
./scripts/deploy-aws.sh
```

## API Documentation

### Interactive Documentation
Once the application is running, access the interactive API documentation:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### Core Endpoints

#### Authentication
```
POST   /api/v1/auth/register     # User registration
POST   /api/v1/auth/login        # User login
POST   /api/v1/auth/refresh      # Refresh access token
GET    /api/v1/auth/me           # Get current user
```

#### Knowledge Management
```
GET    /api/v1/knowledge         # List knowledge items
POST   /api/v1/knowledge         # Create knowledge item
GET    /api/v1/knowledge/{id}    # Get specific item
PUT    /api/v1/knowledge/{id}    # Update item
DELETE /api/v1/knowledge/{id}    # Delete item
POST   /api/v1/knowledge/bulk    # Bulk operations
```

#### Search
```
GET    /api/v1/search            # Basic search
POST   /api/v1/search/vector     # Vector similarity search
POST   /api/v1/search/hybrid     # Hybrid search (text + vector)
GET    /api/v1/search/suggest    # Search suggestions
```

#### Categories
```
GET    /api/v1/categories        # List categories
POST   /api/v1/categories        # Create category
GET    /api/v1/categories/{id}   # Get category details
PUT    /api/v1/categories/{id}   # Update category
DELETE /api/v1/categories/{id}   # Delete category
```

#### Analytics
```
GET    /api/v1/analytics/usage   # Usage statistics
GET    /api/v1/analytics/search  # Search analytics
GET    /api/v1/analytics/trends  # Knowledge trends
POST   /api/v1/analytics/export  # Export analytics data
```

## Configuration

### Environment Variables

Create a `.env` file with the following configuration:

```env
# Application
APP_NAME=KnowledgeDatabase
APP_VERSION=1.0.0
DEBUG=false
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/knowledge_db
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://localhost:6379/0
REDIS_PASSWORD=your-redis-password
REDIS_TTL=3600

# OpenSearch
OPENSEARCH_HOST=localhost
OPENSEARCH_PORT=9200
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=your-opensearch-password

# JWT Settings
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30
JWT_REFRESH_EXPIRATION_DAYS=7

# Rate Limiting
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# Korean NLP
ENABLE_KOREAN_NLP=true
TRANSLATION_SERVICE=googletrans

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### Docker Configuration

The project includes multiple Docker configurations:
- `docker-compose.yml` - Development environment
- `docker-compose.prod.yml` - Production environment
- `docker-compose.test.yml` - Testing environment

## Logging

### Log Management

The application provides comprehensive logging for debugging and monitoring:

#### Log Files
- **Application Logs**: `logs/uvicorn.log` - FastAPI application logs when running in background mode
- **Access Logs**: Included in uvicorn.log with request/response details
- **Error Logs**: Detailed error traces in uvicorn.log

#### Viewing Logs
```bash
# Real-time log monitoring
tail -f logs/uvicorn.log

# View last 100 lines
tail -n 100 logs/uvicorn.log

# Search for errors
grep ERROR logs/uvicorn.log

# View logs with timestamps
less logs/uvicorn.log
```

#### Clean Output Mode
The start script provides clean output by:
- Suppressing Docker Compose warnings
- Converting Alembic migration messages to info level
- Organizing logs in structured format

## Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test categories
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# Run with verbose output
pytest -v

# Run performance tests
pytest tests/performance/ -v
```

### Test Coverage

Current test coverage: **84.9%**

| Component | Coverage | Tests |
|-----------|----------|-------|
| API Endpoints | 92% | 89 |
| Services | 87% | 76 |
| Models | 85% | 45 |
| Middleware | 88% | 52 |
| Auth | 91% | 38 |
| Core | 82% | 45 |
| **Total** | **84.9%** | **345** |

## Performance Metrics

### Benchmarks (M1 Mac Pro, 8GB allocated)

| Metric | Value | Target |
|--------|-------|--------|
| API Response Time (p50) | 45ms | <100ms |
| API Response Time (p99) | 120ms | <500ms |
| Search Latency | 85ms | <200ms |
| Concurrent Users | 500 | >200 |
| Requests per Second | 1,200 | >1,000 |
| Database Connections | 20 | 20-50 |
| Cache Hit Rate | 78% | >70% |

### Optimization Tips

1. **Database**: Use connection pooling and query optimization
2. **Caching**: Implement Redis caching for frequently accessed data
3. **Search**: Use OpenSearch aggregations and filters efficiently
4. **API**: Implement pagination and field filtering
5. **Infrastructure**: Scale horizontally with Docker Swarm or Kubernetes

## Security Features

### Built-in Security

- **Authentication**: JWT-based with refresh tokens
- **Authorization**: Role-based access control (RBAC)
- **Input Validation**: Comprehensive Pydantic schemas
- **SQL Injection Protection**: SQLAlchemy ORM with parameterized queries
- **XSS Protection**: Input sanitization with bleach
- **Rate Limiting**: Per-user and per-IP rate limiting
- **CORS**: Configurable CORS policies
- **Audit Logging**: Complete audit trail for all operations
- **Password Security**: bcrypt hashing with salts
- **HTTPS**: SSL/TLS support with Let's Encrypt

### Security Best Practices

1. Always use HTTPS in production
2. Rotate JWT secrets regularly
3. Implement IP whitelisting for admin endpoints
4. Use environment variables for sensitive data
5. Regular security audits and dependency updates
6. Enable audit logging for compliance
7. Implement backup and disaster recovery

## Known Issues

### Local Development Setup
1. **Dependency Conflicts**: `httpx` and `googletrans` version conflicts - use `requirements-core.txt` for minimal setup
2. **Missing Modules**: `bleach` and `itsdangerous` may need manual installation
3. **pgvector Extension**: Must be manually installed in PostgreSQL container
4. **Port Conflicts**: Port 8000 may be in use - kill existing processes with `pkill -f uvicorn`
5. **Docker Daemon**: Must be running before starting services
6. **Environment Variables**: `.env` file must be created from `.env.example`

### Quick Fix Script
```bash
# Use the automated setup script for quick local setup
./scripts/start-local.sh
```

For detailed troubleshooting, see [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md) and [KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)

## Contributing

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

### Development Workflow

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

### Code Standards

- Follow PEP 8 style guide
- Add type hints to all functions
- Write docstrings for all public APIs
- Maintain test coverage above 85%
- Update documentation for new features

## Deployment

### Local Development (M1 Mac)

See [Local Deployment Guide](docs/deployment/LOCAL_DEPLOYMENT.md) for detailed instructions.

```bash
# Quick deployment
./scripts/deploy-local.sh

# With monitoring stack
./scripts/deploy-local.sh --with-monitoring
```

### AWS Production Deployment

```bash
# Deploy to AWS ECS
./scripts/deploy-aws.sh --env production

# Scale services
aws ecs update-service --cluster kb-cluster --service kb-service --desired-count 3
```

## Monitoring & Maintenance

### Health Checks

```bash
# Application health
curl http://localhost:8000/health

# Database health
curl http://localhost:8000/health/db

# Cache health
curl http://localhost:8000/health/cache

# Search health
curl http://localhost:8000/health/search
```

### Logging

Logs are stored in the `logs/` directory:
- `app.log` - Application logs
- `access.log` - API access logs
- `error.log` - Error logs
- `security.log` - Security events

### Backup & Recovery

```bash
# Backup database
./scripts/backup-local.sh

# Restore from backup
./scripts/restore-local.sh --file backups/backup-20250821.tar.gz

# Automated daily backups
crontab -e
# Add: 0 2 * * * /path/to/scripts/backup-local.sh
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:

- Documentation: [docs/](docs/)
- Issue Tracker: [GitHub Issues](https://github.com/your-org/knowledge-database/issues)
- Email: support@your-org.com
- Slack: #knowledge-database

## Acknowledgments

- FastAPI for the excellent web framework
- OpenSearch for vector search capabilities
- The Python community for amazing libraries
- Contributors and maintainers

---

**Version**: 1.0.0  
**Last Updated**: 2025-08-21  
**Status**: Production Ready