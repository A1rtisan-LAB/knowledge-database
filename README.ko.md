# 지식 데이터베이스 (Knowledge Database)

![빌드 상태](https://img.shields.io/badge/build-passing-brightgreen)
![커버리지](https://img.shields.io/badge/coverage-84.9%25-yellow)
![Python](https://img.shields.io/badge/python-3.11+-blue)
![라이선스](https://img.shields.io/badge/license-MIT-green)
![Docker](https://img.shields.io/badge/docker-ready-blue)
![플랫폼](https://img.shields.io/badge/platform-M1%20Mac%20%7C%20AWS-orange)

## 개요

Knowledge Database는 FastAPI로 구축된 엔터프라이즈급 지식 관리 시스템으로, 벡터 검색, 이중언어 지원(영어/한국어), AI 기반 임베딩 등의 고급 기능을 통해 조직의 지식을 효율적으로 저장, 검색, 관리할 수 있도록 설계되었습니다.

## 주요 기능

### 핵심 기능
- **이중언어 지원**: 영어와 한국어 콘텐츠의 완벽한 지원 및 자동 번역
- **벡터 검색**: OpenSearch와 임베딩을 활용한 AI 기반 의미 검색
- **실시간 캐싱**: 최적화된 성능을 위한 Redis 기반 캐싱 레이어
- **고급 분석**: 사용 추적, 검색 패턴, 지식 인사이트
- **엔터프라이즈 보안**: JWT 인증, 역할 기반 접근 제어, 입력 유효성 검사
- **감사 로깅**: 규정 준수 및 보안을 위한 완전한 감사 추적
- **RESTful API**: OpenAPI/Swagger 지원으로 잘 문서화된 API

### 기술적 특징
- **마이크로서비스 아키텍처**: 명확한 서비스 경계를 가진 모듈식 설계
- **비동기/대기**: 높은 동시성을 위한 완전한 비동기 지원
- **타입 안전성**: Pydantic 검증을 통한 포괄적인 타입 힌트
- **테스트 커버리지**: 345개 이상의 테스트로 84.9% 코드 커버리지
- **프로덕션 준비**: 다중 환경 지원을 위한 Docker 컨테이너화

## 아키텍처 개요

```
┌─────────────────────────────────────────────────────────────┐
│                        클라이언트 레이어                        │
│                   (웹, 모바일, API 클라이언트)                  │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                      API 게이트웨이 (Nginx)                   │
│                    로드 밸런싱 & SSL/TLS                      │
└─────────────────────────────┬───────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────┐
│                    FastAPI 애플리케이션                       │
│  ┌──────────────────────────────────────────────────────┐  │
│  │               미들웨어 레이어                            │  │
│  │  (속도 제한, 로깅, 입력 검증, CORS)                     │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  API 엔드포인트                         │  │
│  │  /auth  /knowledge  /search  /categories  /analytics │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                 서비스 레이어                           │  │
│  │  검색 서비스, 임베딩 서비스, 캐시 서비스                  │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────┬───────────────────────────────┘
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
┌───────▼──────┐     ┌────────▼────────┐   ┌───────▼──────┐
│  PostgreSQL  │     │   OpenSearch    │   │    Redis     │
│  데이터베이스  │     │   벡터 검색      │   │     캐시      │
└──────────────┘     └─────────────────┘   └──────────────┘
```

## 기술 스택

### 백엔드
- **프레임워크**: FastAPI 0.104.1
- **언어**: Python 3.11+
- **서버**: 비동기 지원 Uvicorn

### 데이터 저장소
- **주 데이터베이스**: pgvector 확장을 포함한 PostgreSQL 15
- **검색 엔진**: 벡터 유사도 검색을 위한 OpenSearch 2.x
- **캐시 레이어**: 세션 및 쿼리 캐싱을 위한 Redis 7.x

### 인프라
- **컨테이너화**: Docker & Docker Compose
- **클라우드 플랫폼**: AWS (ECS, RDS, ElastiCache, OpenSearch)
- **로컬 개발**: M1 Mac (ARM64)에 최적화

### 보안 및 인증
- **인증**: 리프레시 메커니즘을 포함한 JWT 토큰
- **암호화**: 비밀번호 해싱을 위한 bcrypt
- **입력 검증**: 살균 기능을 포함한 Pydantic 스키마
- **속도 제한**: 토큰 버킷 알고리즘

### 테스팅 및 품질
- **단위 테스트**: 84.9% 커버리지의 pytest
- **통합 테스트**: 전체 API 엔드포인트 테스트
- **성능 테스트**: locust를 사용한 부하 테스트
- **코드 품질**: black, isort, flake8, mypy

## 설치 방법

### 사전 요구사항

- Python 3.11 이상
- Docker Desktop (M1 Mac: ARM64 버전)
- 최소 8GB RAM (Docker용 6GB)
- 10GB 이상의 디스크 공간

### 빠른 시작

```bash
# 저장소 클론
git clone https://github.com/your-org/knowledge-database.git
cd knowledge-database

# 가상 환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt

# 환경 변수 설정
cp .env.template .env
# .env 파일을 편집하여 설정 입력

# Docker Compose로 서비스 시작
docker-compose up -d

# 데이터베이스 마이그레이션 실행
alembic upgrade head

# 애플리케이션 시작
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 또는 편의 스크립트 사용
./scripts/start-local.sh           # 포그라운드 실행
./scripts/start-local.sh --background  # 백그라운드 실행 (즉시 쉘로 복귀)
```

### 백그라운드 모드 실행

개발 편의를 위한 백그라운드 실행을 지원합니다:

```bash
# 백그라운드 모드로 시작
./scripts/start-local.sh --background

# 애플리케이션 동작:
# - 모든 서비스를 백그라운드에서 시작
# - 즉시 쉘 제어권 반환
# - 로그를 logs/uvicorn.log에 저장

# 로그 모니터링
tail -f logs/uvicorn.log

# 백그라운드 서비스 중지
docker-compose down
```

### 프로덕션 배포 (로컬 M1 Mac)

```bash
# 자동화된 배포 스크립트 사용
chmod +x scripts/deploy-local.sh
./scripts/deploy-local.sh

# 또는 프로덕션 compose 파일로 수동 실행
docker-compose -f docker-compose.prod.yml up -d

# 서비스 상태 확인
curl http://localhost:8000/health
```

### AWS 배포

```bash
# AWS 자격 증명 구성
aws configure

# Terraform으로 인프라 배포
cd infrastructure/terraform
terraform init
terraform plan
terraform apply

# 애플리케이션 배포
./scripts/deploy-aws.sh
```

## API 문서

### 대화형 문서
애플리케이션이 실행되면 대화형 API 문서에 접근할 수 있습니다:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 핵심 엔드포인트

#### 인증
```
POST   /api/v1/auth/register     # 사용자 등록
POST   /api/v1/auth/login        # 사용자 로그인
POST   /api/v1/auth/refresh      # 액세스 토큰 갱신
GET    /api/v1/auth/me           # 현재 사용자 정보
```

#### 지식 관리
```
GET    /api/v1/knowledge         # 지식 항목 목록
POST   /api/v1/knowledge         # 지식 항목 생성
GET    /api/v1/knowledge/{id}    # 특정 항목 조회
PUT    /api/v1/knowledge/{id}    # 항목 업데이트
DELETE /api/v1/knowledge/{id}    # 항목 삭제
POST   /api/v1/knowledge/bulk    # 대량 작업
```

#### 검색
```
GET    /api/v1/search            # 기본 검색
POST   /api/v1/search/vector     # 벡터 유사도 검색
POST   /api/v1/search/hybrid     # 하이브리드 검색 (텍스트 + 벡터)
GET    /api/v1/search/suggest    # 검색 제안
```

#### 카테고리
```
GET    /api/v1/categories        # 카테고리 목록
POST   /api/v1/categories        # 카테고리 생성
GET    /api/v1/categories/{id}   # 카테고리 상세 정보
PUT    /api/v1/categories/{id}   # 카테고리 업데이트
DELETE /api/v1/categories/{id}   # 카테고리 삭제
```

#### 분석
```
GET    /api/v1/analytics/usage   # 사용 통계
GET    /api/v1/analytics/search  # 검색 분석
GET    /api/v1/analytics/trends  # 지식 트렌드
POST   /api/v1/analytics/export  # 분석 데이터 내보내기
```

## 구성

### 환경 변수

다음 구성으로 `.env` 파일을 생성합니다:

```env
# 애플리케이션
APP_NAME=KnowledgeDatabase
APP_VERSION=1.0.0
DEBUG=false
SECRET_KEY=your-secret-key-here
ALLOWED_HOSTS=localhost,127.0.0.1

# 데이터베이스
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

# JWT 설정
JWT_SECRET_KEY=your-jwt-secret
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30
JWT_REFRESH_EXPIRATION_DAYS=7

# 속도 제한
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_PERIOD=60

# 한국어 NLP
ENABLE_KOREAN_NLP=true
TRANSLATION_SERVICE=googletrans

# 로깅
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

### Docker 구성

프로젝트에는 여러 Docker 구성이 포함되어 있습니다:
- `docker-compose.yml` - 개발 환경
- `docker-compose.prod.yml` - 프로덕션 환경
- `docker-compose.test.yml` - 테스트 환경

## 로깅

### 로그 관리

애플리케이션은 디버깅과 모니터링을 위한 포괄적인 로깅을 제공합니다:

#### 로그 파일
- **애플리케이션 로그**: `logs/uvicorn.log` - 백그라운드 모드 실행 시 FastAPI 애플리케이션 로그
- **액세스 로그**: 요청/응답 세부 정보가 포함된 uvicorn.log
- **오류 로그**: uvicorn.log에 상세한 오류 추적 정보

#### 로그 확인
```bash
# 실시간 로그 모니터링
tail -f logs/uvicorn.log

# 최근 100줄 확인
tail -n 100 logs/uvicorn.log

# 오류 검색
grep ERROR logs/uvicorn.log

# 타임스탬프와 함께 로그 확인
less logs/uvicorn.log
```

#### 깔끔한 출력 모드
시작 스크립트는 다음과 같이 깔끔한 출력을 제공합니다:
- Docker Compose 경고 억제
- Alembic 마이그레이션 메시지를 정보 수준으로 변환
- 구조화된 형식으로 로그 구성

## 테스팅

### 테스트 실행

```bash
# 모든 테스트 실행
pytest

# 커버리지와 함께 실행
pytest --cov=app --cov-report=html

# 특정 테스트 카테고리 실행
pytest tests/unit/
pytest tests/integration/
pytest tests/e2e/

# 상세 출력과 함께 실행
pytest -v

# 성능 테스트 실행
pytest tests/performance/ -v
```

### 테스트 커버리지

현재 테스트 커버리지: **84.9%**

| 구성 요소 | 커버리지 | 테스트 수 |
|----------|----------|-----------|
| API 엔드포인트 | 92% | 89 |
| 서비스 | 87% | 76 |
| 모델 | 85% | 45 |
| 미들웨어 | 88% | 52 |
| 인증 | 91% | 38 |
| 코어 | 82% | 45 |
| **전체** | **84.9%** | **345** |

## 성능 지표

### 벤치마크 (M1 Mac Pro, 8GB 할당)

| 지표 | 값 | 목표 |
|------|-----|------|
| API 응답 시간 (p50) | 45ms | <100ms |
| API 응답 시간 (p99) | 120ms | <500ms |
| 검색 지연 시간 | 85ms | <200ms |
| 동시 사용자 | 500 | >200 |
| 초당 요청 수 | 1,200 | >1,000 |
| 데이터베이스 연결 | 20 | 20-50 |
| 캐시 적중률 | 78% | >70% |

### 최적화 팁

1. **데이터베이스**: 연결 풀링 및 쿼리 최적화 사용
2. **캐싱**: 자주 액세스되는 데이터에 Redis 캐싱 구현
3. **검색**: OpenSearch 집계 및 필터를 효율적으로 사용
4. **API**: 페이지네이션 및 필드 필터링 구현
5. **인프라**: Docker Swarm 또는 Kubernetes로 수평 확장

## 보안 기능

### 내장 보안

- **인증**: 리프레시 토큰을 포함한 JWT 기반
- **권한 부여**: 역할 기반 접근 제어 (RBAC)
- **입력 검증**: 포괄적인 Pydantic 스키마
- **SQL 인젝션 방지**: 매개변수화된 쿼리를 사용하는 SQLAlchemy ORM
- **XSS 방지**: bleach를 사용한 입력 살균
- **속도 제한**: 사용자별 및 IP별 속도 제한
- **CORS**: 구성 가능한 CORS 정책
- **감사 로깅**: 모든 작업에 대한 완전한 감사 추적
- **비밀번호 보안**: 솔트를 포함한 bcrypt 해싱
- **HTTPS**: Let's Encrypt를 사용한 SSL/TLS 지원

### 보안 모범 사례

1. 프로덕션에서는 항상 HTTPS 사용
2. JWT 시크릿을 정기적으로 교체
3. 관리자 엔드포인트에 IP 화이트리스트 구현
4. 민감한 데이터는 환경 변수 사용
5. 정기적인 보안 감사 및 종속성 업데이트
6. 규정 준수를 위한 감사 로깅 활성화
7. 백업 및 재해 복구 구현

## 알려진 문제

### 로컬 개발 환경 설정
1. **의존성 충돌**: `httpx`와 `googletrans` 버전 충돌 - 최소 설정을 위해 `requirements-core.txt` 사용
2. **누락된 모듈**: `bleach`와 `itsdangerous`는 수동 설치가 필요할 수 있음
3. **pgvector 확장**: PostgreSQL 컨테이너에 수동으로 설치해야 함
4. **포트 충돌**: 포트 8000이 사용 중일 수 있음 - `pkill -f uvicorn`으로 기존 프로세스 종료
5. **Docker 데몬**: 서비스 시작 전에 Docker가 실행 중이어야 함
6. **환경 변수**: `.env` 파일을 `.env.example`에서 생성해야 함

### 빠른 수정 스크립트
```bash
# 빠른 로컬 설정을 위한 자동화 스크립트 사용
./scripts/start-local.sh
```

자세한 문제 해결은 [TROUBLESHOOTING.ko.md](docs/TROUBLESHOOTING.ko.md)와 [KNOWN_ISSUES.md](docs/KNOWN_ISSUES.md)를 참조하세요.

## 기여하기

기여를 환영합니다! 자세한 내용은 [기여 가이드](CONTRIBUTING.ko.md)를 참조하세요.

### 개발 워크플로우

1. 저장소 포크
2. 기능 브랜치 생성 (`git checkout -b feature/AmazingFeature`)
3. 변경 사항 커밋 (`git commit -m 'Add some AmazingFeature'`)
4. 브랜치에 푸시 (`git push origin feature/AmazingFeature`)
5. Pull Request 생성

### 코드 표준

- PEP 8 스타일 가이드 준수
- 모든 함수에 타입 힌트 추가
- 모든 공개 API에 독스트링 작성
- 85% 이상의 테스트 커버리지 유지
- 새 기능에 대한 문서 업데이트

## 배포

### 로컬 개발 (M1 Mac)

자세한 지침은 [로컬 배포 가이드](docs/deployment/LOCAL_DEPLOYMENT.md)를 참조하세요.

```bash
# 빠른 배포
./scripts/deploy-local.sh

# 모니터링 스택 포함
./scripts/deploy-local.sh --with-monitoring
```

### AWS 프로덕션 배포

```bash
# AWS ECS에 배포
./scripts/deploy-aws.sh --env production

# 서비스 확장
aws ecs update-service --cluster kb-cluster --service kb-service --desired-count 3
```

## 모니터링 및 유지보수

### 상태 확인

```bash
# 애플리케이션 상태
curl http://localhost:8000/health

# 데이터베이스 상태
curl http://localhost:8000/health/db

# 캐시 상태
curl http://localhost:8000/health/cache

# 검색 상태
curl http://localhost:8000/health/search
```

### 로깅

로그는 `logs/` 디렉토리에 저장됩니다:
- `app.log` - 애플리케이션 로그
- `access.log` - API 액세스 로그
- `error.log` - 오류 로그
- `security.log` - 보안 이벤트

### 백업 및 복구

```bash
# 데이터베이스 백업
./scripts/backup-local.sh

# 백업에서 복구
./scripts/restore-local.sh --file backups/backup-20250821.tar.gz

# 자동 일일 백업
crontab -e
# 추가: 0 2 * * * /path/to/scripts/backup-local.sh
```

## 라이선스

이 프로젝트는 MIT 라이선스 하에 라이선스가 부여됩니다 - 자세한 내용은 [LICENSE](LICENSE) 파일을 참조하세요.

## 지원

지원 및 문의:

- 문서: [docs/](docs/)
- 이슈 트래커: [GitHub Issues](https://github.com/your-org/knowledge-database/issues)
- 이메일: support@your-org.com
- Slack: #knowledge-database

## 감사의 말

- 훌륭한 웹 프레임워크를 제공한 FastAPI
- 벡터 검색 기능을 제공한 OpenSearch
- 놀라운 라이브러리를 제공한 Python 커뮤니티
- 기여자와 유지 관리자

---

**버전**: 1.0.0  
**최종 업데이트**: 2025-08-21  
**상태**: 프로덕션 준비 완료