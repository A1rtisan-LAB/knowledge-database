# 🚀 Knowledge Database Developer Guide

## Table of Contents
1. [Development Environment Setup](#development-environment-setup)
2. [Project Structure](#project-structure)
3. [Architecture Overview](#architecture-overview)
4. [Database Schema](#database-schema)
5. [API Development](#api-development)
6. [Testing Strategy](#testing-strategy)
7. [Deployment](#deployment)
8. [Contributing Guidelines](#contributing-guidelines)

## Development Environment Setup

### Prerequisites
- Python 3.11+
- Docker Desktop (M1 Mac optimized)
- PostgreSQL 15
- Redis 7
- OpenSearch 2.x
- Git

### Quick Start
```bash
# Clone repository
git clone <repository-url>
cd knowledge-database

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup environment variables
cp .env.template .env
# Edit .env with your configurations

# Start services with Docker
docker-compose up -d

# Run database migrations
alembic upgrade head

# Start development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### M1 Mac Specific Setup
```bash
# Ensure Docker Desktop is using ARM64 images
docker-compose -f docker-compose.yml up -d

# For native development without Docker
brew install postgresql@15 redis opensearch

# Start services
brew services start postgresql@15
brew services start redis
brew services start opensearch
```

## Project Structure

```
knowledge-database/
├── app/
│   ├── api/                # API endpoints
│   │   ├── v1/             # API version 1
│   │   │   ├── auth.py     # Authentication endpoints
│   │   │   ├── items.py    # Knowledge items CRUD
│   │   │   ├── search.py   # Search functionality
│   │   │   └── admin.py    # Admin endpoints
│   │   └── deps.py         # Dependencies
│   ├── core/               # Core functionality
│   │   ├── config.py       # Configuration
│   │   ├── security.py     # Security utilities
│   │   ├── database.py     # Database connection
│   │   └── exceptions.py   # Custom exceptions
│   ├── models/             # SQLAlchemy models
│   │   ├── user.py
│   │   ├── knowledge_item.py
│   │   └── category.py
│   ├── schemas/            # Pydantic schemas
│   │   ├── user.py
│   │   ├── knowledge_item.py
│   │   └── response.py
│   ├── services/           # Business logic
│   │   ├── auth_service.py
│   │   ├── search_service.py
│   │   └── translation_service.py
│   ├── middleware/         # Custom middleware
│   │   ├── auth.py
│   │   ├── rate_limit.py
│   │   └── logging.py
│   └── main.py            # Application entry point
├── tests/                  # Test suite
│   ├── unit/              # Unit tests
│   ├── integration/       # Integration tests
│   └── e2e/              # End-to-end tests
├── migrations/            # Alembic migrations
├── scripts/              # Utility scripts
├── docs/                 # Documentation
├── docker/              # Docker configurations
└── requirements.txt     # Dependencies
```

## Architecture Overview

### Technology Stack
- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL 15 + pgvector
- **ORM**: SQLAlchemy 2.0
- **Search**: OpenSearch 2.x
- **Cache**: Redis 7
- **Task Queue**: Celery + RabbitMQ
- **Testing**: Pytest + Coverage

### Design Patterns

#### Repository Pattern
```python
# repositories/knowledge_repository.py
class KnowledgeRepository:
    def __init__(self, db: Session):
        self.db = db
    
    async def create(self, item: KnowledgeItemCreate) -> KnowledgeItem:
        db_item = KnowledgeItemModel(**item.dict())
        self.db.add(db_item)
        await self.db.commit()
        return db_item
    
    async def get_by_id(self, item_id: UUID) -> Optional[KnowledgeItem]:
        return await self.db.query(KnowledgeItemModel).filter(
            KnowledgeItemModel.id == item_id
        ).first()
```

#### Service Layer
```python
# services/knowledge_service.py
class KnowledgeService:
    def __init__(self, repo: KnowledgeRepository, search: SearchService):
        self.repo = repo
        self.search = search
    
    async def create_item(self, item: KnowledgeItemCreate) -> KnowledgeItem:
        # Business logic
        db_item = await self.repo.create(item)
        await self.search.index_item(db_item)
        return db_item
```

#### Dependency Injection
```python
# api/deps.py
async def get_db() -> Generator:
    async with SessionLocal() as session:
        yield session

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    # Authentication logic
    return user
```

## Database Schema

### Core Tables

```sql
-- Users table
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    username VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    role VARCHAR(50) DEFAULT 'viewer',
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Knowledge items table
CREATE TABLE knowledge_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title VARCHAR(500) NOT NULL,
    content TEXT NOT NULL,
    summary TEXT,
    category_id UUID REFERENCES categories(id),
    author_id UUID REFERENCES users(id),
    language VARCHAR(10) DEFAULT 'en',
    status VARCHAR(50) DEFAULT 'draft',
    version INTEGER DEFAULT 1,
    embedding vector(768),  -- For semantic search
    tags TEXT[],
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP
);

-- Categories table
CREATE TABLE categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(255) UNIQUE NOT NULL,
    parent_id UUID REFERENCES categories(id),
    description TEXT,
    icon VARCHAR(100),
    sort_order INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for performance
CREATE INDEX idx_items_category ON knowledge_items(category_id);
CREATE INDEX idx_items_author ON knowledge_items(author_id);
CREATE INDEX idx_items_status ON knowledge_items(status);
CREATE INDEX idx_items_language ON knowledge_items(language);
CREATE INDEX idx_items_embedding ON knowledge_items USING ivfflat (embedding vector_cosine_ops);
```

### Migrations
```bash
# Create new migration
alembic revision --autogenerate -m "Add new field"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1
```

## API Development

### Creating New Endpoints

```python
# api/v1/example.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from app.api import deps
from app.schemas import ExampleSchema
from app.services import ExampleService

router = APIRouter()

@router.get("/", response_model=List[ExampleSchema])
async def list_examples(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user)
):
    """List all examples with pagination."""
    service = ExampleService(db)
    return await service.list_examples(skip=skip, limit=limit)

@router.post("/", response_model=ExampleSchema)
async def create_example(
    example: ExampleCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user_with_role("editor"))
):
    """Create a new example."""
    service = ExampleService(db)
    return await service.create_example(example, current_user)
```

### Request/Response Schemas

```python
# schemas/example.py
from pydantic import BaseModel, Field, field_validator
from typing import Optional
from datetime import datetime
from uuid import UUID

class ExampleBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=500)
    content: str = Field(..., min_length=10)
    category_id: UUID

class ExampleCreate(ExampleBase):
    tags: Optional[List[str]] = []
    
    @field_validator('tags')
    @classmethod
    def validate_tags(cls, v):
        if v and len(v) > 10:
            raise ValueError('Maximum 10 tags allowed')
        return v

class ExampleResponse(ExampleBase):
    id: UUID
    author_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

### Error Handling

```python
# core/exceptions.py
class AppException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

class NotFoundException(AppException):
    def __init__(self, detail: str = "Resource not found"):
        super().__init__(status_code=404, detail=detail)

class UnauthorizedException(AppException):
    def __init__(self, detail: str = "Unauthorized"):
        super().__init__(status_code=401, detail=detail)

# Exception handler
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
```

## Testing Strategy

### Test Coverage Requirements
- Unit Tests: 85% minimum coverage
- Integration Tests: All API endpoints
- E2E Tests: Critical user journeys

### Writing Tests

```python
# tests/unit/test_knowledge_service.py
import pytest
from unittest.mock import Mock, AsyncMock
from app.services import KnowledgeService
from app.schemas import KnowledgeItemCreate

@pytest.fixture
def knowledge_service():
    repo = Mock()
    search = Mock()
    return KnowledgeService(repo, search)

@pytest.mark.asyncio
async def test_create_knowledge_item(knowledge_service):
    # Arrange
    item_data = KnowledgeItemCreate(
        title="Test Item",
        content="Test content",
        category_id="123e4567-e89b-12d3-a456-426614174000"
    )
    knowledge_service.repo.create = AsyncMock(return_value=item_data)
    knowledge_service.search.index_item = AsyncMock()
    
    # Act
    result = await knowledge_service.create_item(item_data)
    
    # Assert
    assert result.title == "Test Item"
    knowledge_service.repo.create.assert_called_once_with(item_data)
    knowledge_service.search.index_item.assert_called_once()
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/unit/test_knowledge_service.py

# Run with verbose output
pytest -v

# Run only marked tests
pytest -m "unit"
```

## Deployment

### Local Development

#### Running the Application

The application supports two modes for development:

**Foreground Mode** (See logs in console):
```bash
# Start services and see logs
./scripts/start-local.sh
# Or manually:
docker-compose up
```

**Background Mode** (Recommended for development):
```bash
# Start in background
./scripts/start-local.sh --background
# Application runs in background
# Logs saved to logs/uvicorn.log
# Terminal control returned immediately

# Monitor logs
tail -f logs/uvicorn.log

# View specific log levels
grep INFO logs/uvicorn.log
grep ERROR logs/uvicorn.log

# Stop services
docker-compose down
```

#### Log Management

##### Log Files
- **Application Logs**: 
  - Foreground: Console output
  - Background: `logs/uvicorn.log`
- **Container Logs**: `docker-compose logs -f [service]`
- **Test Logs**: `logs/test-results.log`

##### Logging Configuration
```python
# app/core/logging.py
import logging

# Configure log level
logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for detailed logs
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

##### Clean Output Features
The start script provides:
- Suppressed Docker Compose warnings
- Formatted Alembic migration messages
- Structured log output
- Clear status indicators

#### Development Workflow
```bash
# 1. Start in background for development
./scripts/start-local.sh --background

# 2. Watch logs while developing
tail -f logs/uvicorn.log

# 3. Make code changes (auto-reload enabled)

# 4. Check for errors
grep ERROR logs/uvicorn.log

# 5. Rebuild if needed
docker-compose build app
docker-compose up -d app
```

### Production Deployment

#### Docker Production Build
```bash
# Build production image
docker build -f Dockerfile.prod -t knowledge-database:latest .

# Run production container
docker run -d \
  --name kb-app \
  -p 8000:8000 \
  --env-file .env.production \
  knowledge-database:latest
```

#### AWS Deployment
```bash
# Build and push to ECR
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin <ecr-uri>
docker build -t knowledge-database .
docker tag knowledge-database:latest <ecr-uri>/knowledge-database:latest
docker push <ecr-uri>/knowledge-database:latest

# Deploy with ECS
aws ecs update-service --cluster production --service knowledge-database --force-new-deployment
```

## Contributing Guidelines

### Code Style
- Follow PEP 8 guidelines
- Use Black for formatting
- Use isort for import sorting
- Type hints required for all functions

### Pre-commit Hooks
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/psf/black
    rev: 23.11.0
    hooks:
      - id: black
  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort
  - repo: https://github.com/pycqa/flake8
    rev: 6.1.0
    hooks:
      - id: flake8
```

### Pull Request Process
1. Create feature branch from `develop`
2. Write tests for new functionality
3. Ensure all tests pass
4. Update documentation
5. Submit PR with description
6. Address review comments
7. Merge after approval

### Commit Message Format
```
type(scope): subject

body

footer
```

Types: feat, fix, docs, style, refactor, test, chore

Example:
```
feat(search): add Korean language support

- Integrated Nori tokenizer for Korean text
- Added language detection
- Updated search algorithms

Closes #123
```

---

**Version**: 1.0.0  
**Last Updated**: 2025-08-21  
**Repository**: [GitHub Link]  
**Support**: dev-team@your-domain.com