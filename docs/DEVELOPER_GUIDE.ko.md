# 🚀 Knowledge Database 개발자 가이드

## 목차
1. [개발 환경 설정](#개발-환경-설정)
2. [프로젝트 구조](#프로젝트-구조)
3. [아키텍처 개요](#아키텍처-개요)
4. [데이터베이스 스키마](#데이터베이스-스키마)
5. [API 개발](#api-개발)
6. [테스트 전략](#테스트-전략)
7. [배포](#배포)
8. [기여 가이드라인](#기여-가이드라인)

## 개발 환경 설정

### 필수 요구사항
- Python 3.11+
- Docker Desktop (M1 Mac 최적화)
- PostgreSQL 15
- Redis 7
- OpenSearch 2.x
- Git

### 빠른 시작
```bash
# 저장소 복제
git clone <repository-url>
cd knowledge-database

# 가상 환경 생성
python -m venv venv
source venv/bin/activate  # Windows에서는: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt

# 환경 변수 설정
cp .env.template .env
# .env 파일을 편집하여 설정값 입력

# Docker로 서비스 시작
docker-compose up -d

# 데이터베이스 마이그레이션 실행
alembic upgrade head

# 개발 서버 시작
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### M1 Mac 전용 설정
```bash
# Docker Desktop이 ARM64 이미지를 사용하는지 확인
docker-compose -f docker-compose.yml up -d

# Docker 없이 네이티브 개발 환경 구성
brew install postgresql@15 redis opensearch

# 서비스 시작
brew services start postgresql@15
brew services start redis
brew services start opensearch
```

## 프로젝트 구조

```
knowledge-database/
├── app/
│   ├── api/                # API 엔드포인트
│   │   ├── v1/             # API 버전 1
│   │   │   ├── auth.py     # 인증 엔드포인트
│   │   │   ├── items.py    # 지식 항목 CRUD
│   │   │   ├── search.py   # 검색 기능
│   │   │   └── admin.py    # 관리자 엔드포인트
│   │   └── deps.py         # 의존성
│   ├── core/               # 핵심 기능
│   │   ├── config.py       # 설정
│   │   ├── security.py     # 보안 유틸리티
│   │   ├── database.py     # 데이터베이스 연결
│   │   └── exceptions.py   # 커스텀 예외
│   ├── models/             # SQLAlchemy 모델
│   │   ├── user.py
│   │   ├── knowledge_item.py
│   │   └── category.py
│   ├── schemas/            # Pydantic 스키마
│   │   ├── user.py
│   │   ├── knowledge_item.py
│   │   └── response.py
│   ├── services/           # 비즈니스 로직
│   │   ├── auth_service.py
│   │   ├── search_service.py
│   │   └── translation_service.py
│   ├── middleware/         # 커스텀 미들웨어
│   │   ├── auth.py
│   │   ├── rate_limit.py
│   │   └── logging.py
│   └── main.py            # 애플리케이션 진입점
├── tests/                  # 테스트 스위트
│   ├── unit/              # 단위 테스트
│   ├── integration/       # 통합 테스트
│   └── e2e/              # End-to-End 테스트
├── migrations/            # Alembic 마이그레이션
├── scripts/              # 유틸리티 스크립트
├── docs/                 # 문서
├── docker/              # Docker 설정
└── requirements.txt     # 의존성
```

## 아키텍처 개요

### 기술 스택
- **Framework**: FastAPI 0.104.1
- **Database**: PostgreSQL 15 + pgvector
- **ORM**: SQLAlchemy 2.0
- **Search**: OpenSearch 2.x
- **Cache**: Redis 7
- **Task Queue**: Celery + RabbitMQ
- **Testing**: Pytest + Coverage

### 디자인 패턴

#### Repository 패턴
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

#### Service 레이어
```python
# services/knowledge_service.py
class KnowledgeService:
    def __init__(self, repo: KnowledgeRepository, search: SearchService):
        self.repo = repo
        self.search = search
    
    async def create_item(self, item: KnowledgeItemCreate) -> KnowledgeItem:
        # 비즈니스 로직
        db_item = await self.repo.create(item)
        await self.search.index_item(db_item)
        return db_item
```

#### 의존성 주입 (Dependency Injection)
```python
# api/deps.py
async def get_db() -> Generator:
    async with SessionLocal() as session:
        yield session

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    # 인증 로직
    return user
```

## 데이터베이스 스키마

### 핵심 테이블

```sql
-- 사용자 테이블
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

-- 지식 항목 테이블
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
    embedding vector(768),  -- 시맨틱 검색용
    tags TEXT[],
    metadata JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    published_at TIMESTAMP
);

-- 카테고리 테이블
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

-- 성능을 위한 인덱스 생성
CREATE INDEX idx_items_category ON knowledge_items(category_id);
CREATE INDEX idx_items_author ON knowledge_items(author_id);
CREATE INDEX idx_items_status ON knowledge_items(status);
CREATE INDEX idx_items_language ON knowledge_items(language);
CREATE INDEX idx_items_embedding ON knowledge_items USING ivfflat (embedding vector_cosine_ops);
```

### 마이그레이션
```bash
# 새 마이그레이션 생성
alembic revision --autogenerate -m "Add new field"

# 마이그레이션 적용
alembic upgrade head

# 마이그레이션 롤백
alembic downgrade -1
```

## API 개발

### 새 엔드포인트 생성

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
    """페이지네이션을 사용하여 모든 예제 목록 조회"""
    service = ExampleService(db)
    return await service.list_examples(skip=skip, limit=limit)

@router.post("/", response_model=ExampleSchema)
async def create_example(
    example: ExampleCreate,
    db: Session = Depends(deps.get_db),
    current_user: User = Depends(deps.get_current_user_with_role("editor"))
):
    """새 예제 생성"""
    service = ExampleService(db)
    return await service.create_example(example, current_user)
```

### 요청/응답 스키마

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
            raise ValueError('최대 10개의 태그만 허용됩니다')
        return v

class ExampleResponse(ExampleBase):
    id: UUID
    author_id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True
```

### 오류 처리

```python
# core/exceptions.py
class AppException(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail

class NotFoundException(AppException):
    def __init__(self, detail: str = "리소스를 찾을 수 없습니다"):
        super().__init__(status_code=404, detail=detail)

class UnauthorizedException(AppException):
    def __init__(self, detail: str = "권한이 없습니다"):
        super().__init__(status_code=401, detail=detail)

# 예외 핸들러
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )
```

## 테스트 전략

### 테스트 커버리지 요구사항
- 단위 테스트: 최소 85% 커버리지
- 통합 테스트: 모든 API 엔드포인트
- E2E 테스트: 중요한 사용자 여정

### 테스트 작성

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
    # 준비 (Arrange)
    item_data = KnowledgeItemCreate(
        title="테스트 항목",
        content="테스트 내용",
        category_id="123e4567-e89b-12d3-a456-426614174000"
    )
    knowledge_service.repo.create = AsyncMock(return_value=item_data)
    knowledge_service.search.index_item = AsyncMock()
    
    # 실행 (Act)
    result = await knowledge_service.create_item(item_data)
    
    # 검증 (Assert)
    assert result.title == "테스트 항목"
    knowledge_service.repo.create.assert_called_once_with(item_data)
    knowledge_service.search.index_item.assert_called_once()
```

### 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 커버리지와 함께 실행
pytest --cov=app --cov-report=html

# 특정 테스트 파일 실행
pytest tests/unit/test_knowledge_service.py

# 상세 출력과 함께 실행
pytest -v

# 마킹된 테스트만 실행
pytest -m "unit"
```

## 배포

### 로컬 개발

#### 애플리케이션 실행

개발을 위해 두 가지 모드를 지원합니다:

**포그라운드 모드** (콘솔에서 로그 확인):
```bash
# 서비스 시작 및 로그 확인
./scripts/start-local.sh
# 또는 수동으로:
docker-compose up
```

**백그라운드 모드** (개발 시 권장):
```bash
# 백그라운드로 시작
./scripts/start-local.sh --background
# 백그라운드에서 애플리케이션 실행
# 로그는 logs/uvicorn.log에 저장
# 즉시 터미널 제어권 반환

# 로그 모니터링
tail -f logs/uvicorn.log

# 특정 로그 레벨 확인
grep INFO logs/uvicorn.log
grep ERROR logs/uvicorn.log

# 서비스 중지
docker-compose down
```

#### 로그 관리

##### 로그 파일
- **애플리케이션 로그**: 
  - 포그라운드: 콘솔 출력
  - 백그라운드: `logs/uvicorn.log`
- **컨테이너 로그**: `docker-compose logs -f [service]`
- **테스트 로그**: `logs/test-results.log`

##### 로깅 설정
```python
# app/core/logging.py
import logging

# 로그 레벨 설정
logging.basicConfig(
    level=logging.INFO,  # 상세 로그를 위해 DEBUG로 변경
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

##### 깔끔한 출력 기능
시작 스크립트가 제공하는 기능:
- Docker Compose 경고 억제
- Alembic 마이그레이션 메시지 포맷팅
- 구조화된 로그 출력
- 명확한 상태 표시기

#### 개발 워크플로우
```bash
# 1. 개발을 위해 백그라운드로 시작
./scripts/start-local.sh --background

# 2. 개발하면서 로그 모니터링
tail -f logs/uvicorn.log

# 3. 코드 변경 (자동 리로드 활성화)

# 4. 오류 확인
grep ERROR logs/uvicorn.log

# 5. 필요 시 재빌드
docker-compose build app
docker-compose up -d app
```

### 프로덕션 배포

#### Docker 프로덕션 빌드
```bash
# 프로덕션 이미지 빌드
docker build -f Dockerfile.prod -t knowledge-database:latest .

# 프로덕션 컨테이너 실행
docker run -d \
  --name kb-app \
  -p 8000:8000 \
  --env-file .env.production \
  knowledge-database:latest
```

#### AWS 배포
```bash
# ECR에 빌드 및 푸시
aws ecr get-login-password --region ap-northeast-2 | docker login --username AWS --password-stdin <ecr-uri>
docker build -t knowledge-database .
docker tag knowledge-database:latest <ecr-uri>/knowledge-database:latest
docker push <ecr-uri>/knowledge-database:latest

# ECS로 배포
aws ecs update-service --cluster production --service knowledge-database --force-new-deployment
```

## 기여 가이드라인

### 코드 스타일
- PEP 8 가이드라인 준수
- Black을 사용한 포맷팅
- isort를 사용한 import 정렬
- 모든 함수에 타입 힌트 필수

### Pre-commit 훅
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

### Pull Request 프로세스
1. `develop` 브랜치에서 feature 브랜치 생성
2. 새 기능에 대한 테스트 작성
3. 모든 테스트 통과 확인
4. 문서 업데이트
5. 설명과 함께 PR 제출
6. 리뷰 코멘트 처리
7. 승인 후 머지

### 커밋 메시지 형식
```
type(scope): subject

body

footer
```

타입: feat, fix, docs, style, refactor, test, chore

예시:
```
feat(search): 한국어 언어 지원 추가

- 한국어 텍스트를 위한 Nori 토크나이저 통합
- 언어 감지 기능 추가
- 검색 알고리즘 업데이트

Closes #123
```

---

**버전**: 1.0.0  
**최종 업데이트**: 2025-08-21  
**저장소**: [GitHub 링크]  
**지원**: dev-team@your-domain.com