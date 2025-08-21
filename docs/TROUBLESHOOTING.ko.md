# 🔧 Knowledge Database 문제 해결 가이드

## 목차
1. [일반적인 문제](#일반적인-문제)
2. [설치 문제](#설치-문제)
3. [런타임 오류](#런타임-오류)
4. [성능 문제](#성능-문제)
5. [데이터베이스 문제](#데이터베이스-문제)
6. [검색 문제](#검색-문제)
7. [인증 및 권한](#인증-및-권한)
8. [Docker 및 배포](#docker-및-배포)
9. [M1 Mac 특정 문제](#m1-mac-특정-문제)
10. [비상 절차](#비상-절차)

## 일반적인 문제

### 애플리케이션이 시작되지 않음

#### 증상
```
ERROR: Application failed to start
```

#### 진단 및 해결
```bash
# 모든 서비스가 실행 중인지 확인
docker-compose ps

# 애플리케이션 로그 확인
docker logs kb-app-prod

# 일반적인 원인:
# 1. 데이터베이스 연결 실패
psql -h localhost -U kb_user -d knowledge_db -c "SELECT 1"

# 2. 포트가 이미 사용 중
lsof -i :8000
kill -9 <PID>

# 3. 환경 변수 누락
cat .env
# 모든 필수 변수가 설정되어 있는지 확인

# 4. 의존성이 설치되지 않음
pip install -r requirements.txt
```

### 빠른 로컬 설정 스크립트

빠른 로컬 설정을 위해 자동화 스크립트를 사용하세요:
```bash
# 스크립트를 실행 가능하게 만들기
chmod +x scripts/start-local.sh

# 스크립트 실행
./scripts/start-local.sh

# 이 스크립트가 처리하는 작업:
# - Docker 데몬 확인 및 시작
# - 환경 파일 생성
# - PostgreSQL 확장 설정
# - 의존성 설치
# - 데이터베이스 마이그레이션
# - 애플리케이션 시작
```

### Import 오류

#### 증상
```python
ModuleNotFoundError: No module named 'app'
```

#### 해결 방법
```bash
# 프로젝트를 Python 경로에 추가
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 또는 가상 환경에서
pip install -e .

# 설치 확인
python -c "import app; print(app.__file__)"
```

## 설치 문제

### Python 의존성 충돌

#### 증상
```
ERROR: Cannot install httpx==0.25.2 and googletrans 4.0.0-rc1 because these package versions have conflicting dependencies
```

#### 해결 방법
```bash
# 유연한 버전 제약 사용
# requirements.txt 편집:
httpx>=0.13.3  # httpx==0.25.2 대신

# 또는 최소 요구사항 사용
pip install -r requirements-core.txt

# 충돌하는 패키지 주석 처리
# googletrans==4.0.0-rc1  # httpx와 충돌
```

### 누락된 Python 모듈

#### 증상
```
ModuleNotFoundError: No module named 'bleach'
ModuleNotFoundError: No module named 'itsdangerous'
```

#### 해결 방법
```bash
# 누락된 패키지 설치
pip install bleach itsdangerous opensearch-py

# 이들은 종종 requirements.txt에서 누락됨
# requirements.txt에 추가:
bleach==6.1.0
itsdangerous==2.2.0
```

### Docker Compose 실패

#### 증상
```
ERROR: Service 'opensearch' failed to build
```

#### 해결 방법
```bash
# Docker 캐시 정리
docker system prune -a

# 캐시 없이 재빌드
docker-compose build --no-cache

# M1 Mac에서 메모리 문제인 경우
# Docker Desktop 메모리를 최소 6GB로 증가
# 설정 → Resources → Advanced → Memory: 6GB
```

### Docker 데몬이 실행되지 않음

#### 증상
```
Cannot connect to the Docker daemon at unix:///var/run/docker.sock
```

#### 해결 방법
```bash
# macOS에서
open -a Docker

# Docker 시작 대기
sleep 30

# Docker 실행 확인
docker info

# Linux에서
sudo systemctl start docker
sudo systemctl enable docker
```

### PostgreSQL 연결 실패

#### 증상
```
psycopg2.OperationalError: connection to server failed
```

#### 해결 방법
```bash
# PostgreSQL이 실행 중인지 확인
docker-compose ps postgres

# 연결 테스트
docker exec -it kb-postgres-prod psql -U kb_user -d knowledge_db

# 설정 확인
cat docker-compose.yml | grep -A 5 postgres

# 네트워크 확인
docker network ls
docker network inspect knowledge-database_default
```

### pgvector 확장이 설치되지 않음

#### 증상
```
ERROR: type "vector" does not exist
```

#### 해결 방법
```bash
# PostgreSQL에 pgvector 확장 설치
docker exec knowledge-postgres psql -U postgres -d knowledge_db -c "CREATE EXTENSION IF NOT EXISTS vector;"

# uuid 확장도 필요한 경우 설치
docker exec knowledge-postgres psql -U postgres -d knowledge_db -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"

# 또는 docker-compose.yml volumes에 추가:
volumes:
  - ./migrations/init.sql:/docker-entrypoint-initdb.d/init.sql

# migrations/init.sql 생성:
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
```

### 포트 8000이 이미 사용 중

#### 증상
```
[Errno 48] Address already in use
[Errno 98] Address already in use
```

#### 해결 방법
```bash
# 포트 8000을 사용하는 프로세스 찾기
lsof -i :8000

# 기존 uvicorn 프로세스 종료
pkill -f uvicorn

# 또는 특정 PID 종료
kill -9 <PID>

# 필요한 경우 다른 포트 사용
uvicorn app.main:app --port 8001
```

### 환경 변수가 설정되지 않음

#### 증상
```
ValueError: [SECRET_KEY] not found in environment
```

#### 해결 방법
```bash
# 예제에서 .env 생성
cp .env.example .env

# 안전한 SECRET_KEY 생성
python -c "import secrets; print(secrets.token_urlsafe(32))"

# .env 파일 업데이트
SECRET_KEY=여기에_생성된_시크릿_키_입력

# 환경 변수 소스
source .env
# 또는 python-dotenv 사용
```

### OpenSearch가 시작되지 않음

#### 증상
```
OpenSearch 컨테이너가 코드 137로 종료됨 (OOM)
```

#### 해결 방법
```bash
# 메모리 제한 증가
# docker-compose.yml 편집
services:
  opensearch:
    environment:
      - "OPENSEARCH_JAVA_OPTS=-Xms1g -Xmx1g"
    mem_limit: 2g

# 호스트 시스템에서 vm.max_map_count 증가
sudo sysctl -w vm.max_map_count=262144

# 영구적으로 설정
echo "vm.max_map_count=262144" | sudo tee -a /etc/sysctl.conf
```

## 런타임 오류

### Pydantic 유효성 검사 오류

#### 증상
```python
pydantic.error_wrappers.ValidationError: 1 validation error for Settings
```

#### 해결 방법
```python
# 환경 변수 형식 확인
# .env 파일
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/db
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secret-key-minimum-32-chars

# 환경 변수의 리스트
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

### JWT 토큰 오류

#### 증상
```
jose.exceptions.JWTError: Invalid token
```

#### 해결 방법
```python
# SECRET_KEY가 설정되어 있는지 확인
import os
print(os.getenv("SECRET_KEY"))

# 토큰 만료 확인
from datetime import datetime, timedelta
ACCESS_TOKEN_EXPIRE_MINUTES = 30

# 토큰 형식 확인
# 형식: Bearer <token>
headers = {"Authorization": "Bearer eyJ..."}

# 토큰 문제가 지속되면 Redis 캐시 정리
redis-cli FLUSHDB
```

## 성능 문제

### 느린 API 응답 시간

#### 진단
```bash
# 리소스 사용량 확인
docker stats

# 데이터베이스 쿼리 모니터링
docker exec -it kb-postgres-prod psql -U kb_user -d knowledge_db
\x
SELECT query, calls, mean_exec_time 
FROM pg_stat_statements 
ORDER BY mean_exec_time DESC 
LIMIT 10;
```

#### 해결 방법
```python
# 1. 데이터베이스 인덱스 추가
CREATE INDEX idx_items_created ON knowledge_items(created_at DESC);
CREATE INDEX idx_items_category ON knowledge_items(category_id);

# 2. 캐싱 구현
from app.core.cache import cache

@cache(expire=300)
async def get_popular_items():
    # 5분 동안 캐시되는 비용이 많이 드는 쿼리
    pass

# 3. 페이지네이션 사용
@router.get("/items")
async def list_items(skip: int = 0, limit: int = 100):
    # 결과 제한
    pass

# 4. 쿼리 최적화
# 조인에 select_related 사용
items = db.query(Item).options(selectinload(Item.category)).all()
```

### 높은 메모리 사용량

#### 진단
```bash
# 컨테이너별 메모리 사용량 확인
docker stats --no-stream

# Python에서 메모리 누수 찾기
pip install memory_profiler
python -m memory_profiler app/main.py
```

#### 해결 방법
```bash
# 1. 워커 연결 제한
gunicorn app.main:app \
  --workers 2 \
  --worker-connections 100 \
  --max-requests 1000 \
  --max-requests-jitter 50

# 2. 주기적으로 캐시 정리
redis-cli
> INFO memory
> FLUSHDB

# 3. Docker 메모리 최적화
docker update --memory="1g" --memory-swap="2g" kb-app-prod
```

## 데이터베이스 문제

### 마이그레이션 실패

#### 증상
```
alembic.util.exc.CommandError: Can't locate revision identified by 'head'
```

#### 해결 방법
```bash
# 마이그레이션 히스토리 확인
alembic history

# 현재 데이터베이스 상태 스탬프
alembic stamp head

# 새 마이그레이션 생성
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head

# 필요시 롤백
alembic downgrade -1
```

### 연결 풀 고갈

#### 증상
```
sqlalchemy.exc.TimeoutError: QueuePool limit exceeded
```

#### 해결 방법
```python
# database.py에서 풀 크기 증가
engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=40,
    pool_pre_ping=True,
    pool_recycle=3600
)

# 연결 모니터링
SELECT count(*) FROM pg_stat_activity;

# 유휴 연결 종료
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' 
AND state_change < now() - interval '10 minutes';
```

## 검색 문제

### OpenSearch 인덱스 누락

#### 증상
```
opensearchpy.exceptions.NotFoundError: index not found
```

#### 해결 방법
```bash
# 인덱스 생성
curl -X PUT "localhost:9200/knowledge_items" \
  -H 'Content-Type: application/json' \
  -d @configs/opensearch/index_mapping.json

# 모든 데이터 재색인
docker exec -it kb-app-prod python scripts/reindex.py

# 인덱스 상태 확인
curl -X GET "localhost:9200/_cat/indices?v"
```

### 한국어 검색이 작동하지 않음

#### 증상
한국어 텍스트가 결과를 반환하지 않음

#### 해결 방법
```json
// 분석기 설정 업데이트
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

// 새 분석기로 재색인
POST _reindex
{
  "source": {"index": "knowledge_items"},
  "dest": {"index": "knowledge_items_v2"}
}
```

## 인증 및 권한

### 로그인 실패

#### 진단
```python
# 비밀번호 해싱 확인
from passlib.context import CryptContext
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
print(pwd_context.hash("test_password"))

# 사용자 존재 확인
docker exec -it kb-postgres-prod psql -U kb_user -d knowledge_db
SELECT email, is_active FROM users WHERE email = 'user@example.com';
```

### 권한 거부

#### 해결 방법
```python
# 사용자 역할 확인
SELECT role FROM users WHERE email = 'user@example.com';

# 필요시 사용자 역할 업데이트
UPDATE users SET role = 'editor' WHERE email = 'user@example.com';

# 역할 변경 후 캐시 정리
redis-cli DEL user_cache:user@example.com
```

## Docker 및 배포

### OpenSearch Dashboards Locale 오류

#### 증상
```
[I18n] A `locale` must be a non-empty string to add messages.
Version: 2.11.0
Build: 6665
Error: [I18n] A `locale` must be a non-empty string to add messages.
```

#### 원인
이 오류는 OpenSearch Dashboards가 i18n(국제화) 시스템을 제대로 초기화하지 못할 때 발생하며, 주로 누락되거나 잘못 구성된 locale 설정 때문입니다.

#### 해결 방법
1. **OpenSearch Dashboards 설정 파일 생성**:
```yaml
# opensearch-dashboards.yml
server.host: "0.0.0.0"
server.port: 5601

opensearch.hosts: ["http://opensearch:9200"]
opensearch.ssl.verificationMode: none

# locale 문제 해결
i18n.locale: "en"

logging.dest: stdout
logging.verbose: false

map.includeOpenSearchMapsService: false
```

2. **docker-compose.yml 업데이트**하여 설정 사용:
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

3. **브라우저 캐시 지우기** 및 컨테이너 재시작:
```bash
docker restart knowledge-opensearch-dashboards
# 브라우저 캐시 지우기 (Ctrl+Shift+R 또는 Cmd+Shift+R)
# 또는 시크릿/프라이빗 브라우징 모드에서 시도
```

4. **대안: UI 문제가 지속되면 API 직접 사용**:
```bash
# OpenSearch 상태 확인
curl http://localhost:9200/_cluster/health?pretty

# 인덱스 목록 확인
curl http://localhost:9200/_cat/indices?v

# 데이터 검색
curl -X GET "localhost:9200/knowledge_items/_search?pretty"
```

### 컨테이너가 계속 재시작됨

#### 진단
```bash
# 컨테이너 로그 확인
docker logs --tail 50 kb-app-prod

# 종료 코드 확인
docker inspect kb-app-prod --format='{{.State.ExitCode}}'

# 일반적인 종료 코드:
# 0 - 성공
# 1 - 일반 오류
# 125 - Docker 데몬 오류
# 126 - 컨테이너 명령 실행 불가
# 127 - 컨테이너 명령을 찾을 수 없음
# 137 - 메모리 부족 (OOM)
# 139 - 세그멘테이션 오류
```

### M1 Mac에서 빌드 실패

#### 해결 방법
```dockerfile
# Dockerfile에서 플랫폼 지정
FROM --platform=linux/arm64 python:3.11-slim

# 또는 docker-compose.yml에서
services:
  app:
    platform: linux/arm64
    build:
      context: .
      dockerfile: Dockerfile
```

## M1 Mac 특정 문제

### 아키텍처 불일치

#### 증상
```
WARNING: The requested image's platform (linux/amd64) does not match the detected host platform (linux/arm64/v8)
```

#### 해결 방법
```bash
# ARM64 호환 이미지 사용
docker pull --platform linux/arm64 postgres:15
docker pull --platform linux/arm64 redis:7-alpine
docker pull --platform linux/arm64 opensearchproject/opensearch:2.11.0

# 멀티 아키텍처용 buildx로 빌드
docker buildx build --platform linux/arm64,linux/amd64 -t myapp:latest .
```

### Rosetta 2 성능 문제

#### 해결 방법
```bash
# Docker Desktop에서 Rosetta 2 활성화
# 설정 → Features in development → x86/amd64 에뮬레이션용 Rosetta 사용

# 또는 네이티브 ARM 이미지 사용
# docker-compose.yml을 ARM 특정 태그로 업데이트
image: postgres:15-alpine  # ARM64 호환
```

## 비상 절차

### 전체 시스템 복구

```bash
#!/bin/bash
# emergency_recovery.sh

echo "비상 복구 시작..."

# 1. 모든 서비스 중지
docker-compose down

# 2. 현재 상태 백업
mkdir -p backups/emergency_$(date +%Y%m%d_%H%M%S)
docker exec kb-postgres-prod pg_dump -U kb_user knowledge_db > backups/emergency_$(date +%Y%m%d_%H%M%S)/database.sql

# 3. 정리
docker system prune -f
docker volume prune -f

# 4. 마지막으로 알려진 정상 백업에서 복원
docker-compose up -d postgres
sleep 10
docker exec -i kb-postgres-prod psql -U kb_user knowledge_db < backups/last_known_good.sql

# 5. 서비스를 하나씩 시작
docker-compose up -d redis
docker-compose up -d opensearch
sleep 30
docker-compose up -d app
docker-compose up -d nginx

# 6. 상태 확인
curl http://localhost:8000/health

echo "복구 완료. 시스템 기능을 확인하세요."
```

### 데이터 손상 복구

```sql
-- 손상 확인
SELECT schemaname, tablename, 
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- 손상된 인덱스 재구축
REINDEX TABLE knowledge_items;
REINDEX DATABASE knowledge_db;

-- Vacuum 및 분석
VACUUM FULL ANALYZE;
```

### 성능 비상 상황

```bash
# 빠른 성능 개선
# 1. 모든 캐시 정리
redis-cli FLUSHALL

# 2. 워커 수를 줄여 애플리케이션 재시작
docker-compose scale app=1

# 3. 중요하지 않은 기능 비활성화
export DISABLE_ANALYTICS=true
export DISABLE_TRANSLATIONS=true

# 4. 일시적으로 타임아웃 증가
export REQUEST_TIMEOUT=60
export DATABASE_POOL_TIMEOUT=30

# 5. 모니터링 및 점진적 복원
docker stats --no-stream
```

## 도움 받기

### 로그 위치

#### 애플리케이션 로그
**포그라운드 모드**:
- 콘솔 출력 (터미널에서 확인 가능)
- Ctrl+C로 중지하고 전체 로그 확인

**백그라운드 모드**:
- 로그 저장 위치: `logs/uvicorn.log`
- 로그 확인: `tail -f logs/uvicorn.log`
- 오류 확인: `grep ERROR logs/uvicorn.log`
- 최근 100줄: `tail -n 100 logs/uvicorn.log`

#### 컨테이너 로그
- 애플리케이션: `docker logs kb-app-prod`
- PostgreSQL: `docker logs kb-postgres-prod`
- OpenSearch: `docker logs kb-opensearch-prod`
- Redis: `docker logs kb-redis-prod`
- Nginx: `docker logs kb-nginx-prod`

#### 로그 분석 명령어
```bash
# 특정 오류 패턴 검색
grep -i "connection refused" logs/uvicorn.log
grep -i "timeout" logs/uvicorn.log
grep -i "memory" logs/uvicorn.log

# 오류 발생 횟수 확인
grep -c ERROR logs/uvicorn.log

# 타임스탬프와 함께 로그 확인
less logs/uvicorn.log

# 여러 로그 파일 모니터링
tail -f logs/*.log
```

### 디버그 모드

#### 디버그 로깅 활성화
```bash
# 포그라운드 모드용
export LOG_LEVEL=DEBUG
export SQLALCHEMY_ECHO=true
./scripts/start-local.sh

# 백그라운드 모드용
export LOG_LEVEL=DEBUG
export SQLALCHEMY_ECHO=true
./scripts/start-local.sh --background
tail -f logs/uvicorn.log  # 디버그 출력 모니터링
```

#### 깔끔한 출력 기능
시작 스크립트 사용 시:
- Docker Compose 경고가 억제됨
- Alembic 마이그레이션 메시지가 깔끔하게 포맷팅됨
- 로그가 구조화되고 조직화됨
- 명확한 상태 표시기가 서비스 상태를 표시

#### 백그라운드 모드 문제 해결
```bash
# 서비스 실행 상태 확인
docker-compose ps

# 백그라운드 로그 확인
tail -f logs/uvicorn.log

# 백그라운드 서비스 중지
docker-compose down

# 깨끗한 재시작
docker-compose down
./scripts/start-local.sh --background
```

### 지원 연락처
- **시스템 관리자**: admin@your-domain.com
- **개발팀**: dev-team@your-domain.com
- **비상 연락처**: +1-XXX-XXX-XXXX
- **문서**: https://docs.your-domain.com

---

**버전**: 1.0.0  
**최종 업데이트**: 2025-08-21  
**비상 핫라인**: 프로덕션 다운 시 연락