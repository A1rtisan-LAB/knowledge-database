# 🏠 로컬 배포 가이드 (M1 Mac)

## 📦 개요

이 가이드는 M1 MacBook Pro에서 Knowledge Database를 프로덕션 환경으로 배포하는 방법을 설명합니다.

## 🔧 사전 요구사항

- Docker Desktop for Mac (M1/Apple Silicon)
- 최소 8GB RAM 할당 (권장: 6GB Docker)
- 10GB 이상의 디스크 공간
- Git

## 🚀 빠른 시작

```bash
# 1. 저장소 클론
git clone <repository-url>
cd knowledge-database

# 2. 환경 변수 설정
cp .env.template .env.production
# .env.production 파일을 편집하여 필요한 값 설정

# 3. 배포 실행
chmod +x scripts/deploy-local.sh
./scripts/deploy-local.sh

# 또는 옵션과 함께 시작 스크립트 사용
chmod +x scripts/start-local.sh
./scripts/start-local.sh           # 포그라운드 모드
./scripts/start-local.sh --background  # 백그라운드 모드
```

### 스크립트 옵션

`start-local.sh` 스크립트는 여러 옵션을 지원합니다:

```bash
# 포그라운드에서 실행 (기본값)
./scripts/start-local.sh

# 백그라운드 모드로 실행
./scripts/start-local.sh --background
# - 즉시 쉘 제어권 반환
# - 로그는 logs/uvicorn.log에 저장
# - 개발 워크플로우에 완벽

# 백그라운드 로그 모니터링
tail -f logs/uvicorn.log

# 백그라운드 서비스 중지
docker-compose down
```

## 🎯 실행 모드

### 포그라운드 모드 (기본값)
- 현재 터미널에서 애플리케이션 실행
- 콘솔에 로그 표시
- 터미널이 계속 사용 중 상태
- Ctrl+C로 중지

### 백그라운드 모드
- 백그라운드에서 애플리케이션 실행
- 즉시 터미널 제어권 반환
- 로그는 `logs/uvicorn.log`에 저장
- 개발 및 테스트에 완벽

```bash
# 백그라운드로 시작
./scripts/start-local.sh --background

# 실행 상태 확인
docker-compose ps

# 로그 모니터링
tail -f logs/uvicorn.log

# 서비스 중지
docker-compose down
```

## 📝 상세 설정

### 1. 환경 변수 설정

`.env.production` 파일에서 다음 변수들을 설정:

```env
# 보안
SECRET_KEY=your-secret-key-here  # 강력한 비밀 키 생성

# 데이터베이스
DB_USER=kb_user
DB_PASSWORD=strong-password-here

# Redis
REDIS_PASSWORD=redis-password-here

# OpenSearch
OPENSEARCH_USER=admin
OPENSEARCH_PASSWORD=opensearch-password
```

### 2. Docker Compose 구성

`docker-compose.prod.yml` 주요 서비스:

- **PostgreSQL**: 메인 데이터베이스 (포트 5432)
- **Redis**: 캐싱 레이어 (포트 6379)
- **OpenSearch**: 검색 엔진 (포트 9200)
- **Application**: FastAPI 앱 (포트 8000)
- **Nginx**: 리버스 프록시 (포트 80/443)

### 3. 배포 스크립트 옵션

```bash
# 전체 배포 (기본)
./scripts/deploy-local.sh

# 앱만 재배포
./scripts/deploy-local.sh --app-only

# 데이터베이스 백업 포함
./scripts/deploy-local.sh --with-backup

# 개발 모드 (로그 상세 출력)
./scripts/deploy-local.sh --debug
```

## 📈 모니터링

### 서비스 상태 확인

```bash
# 모든 서비스 상태
docker-compose -f docker-compose.prod.yml ps

# 헬스체크
curl http://localhost:8000/health

# 로그 확인
docker-compose -f docker-compose.prod.yml logs -f app
```

### Prometheus + Grafana (선택사항)

```bash
# 모니터링 스택 시작
docker-compose -f docker-compose.monitoring.yml up -d

# Grafana 접속: http://localhost:3000
# 기본 계정: admin/admin
```

## 🗓️ 백업 및 복구

### 백업

```bash
# 전체 백업
./scripts/backup-local.sh

# 데이터베이스만 백업
./scripts/backup-local.sh --db-only

# 백업 위치: ./backups/
```

### 복구

```bash
# 최신 백업에서 복구
./scripts/restore-local.sh

# 특정 백업 파일에서 복구
./scripts/restore-local.sh --file backups/backup-20250821.tar.gz
```

## 🔄 업데이트

```bash
# 1. 코드 업데이트
git pull origin main

# 2. 이미지 재빌드
docker build -f Dockerfile.prod -t knowledge-database:latest .

# 3. 서비스 재시작 (무중단)
docker-compose -f docker-compose.prod.yml up -d --no-deps app

# 4. 마이그레이션 실행
docker exec kb-app-prod alembic upgrade head
```

## 🎯 성능 최적화

### M1 Mac 최적화

1. **Docker Desktop 설정**:
   - Settings → Resources → Advanced
   - CPUs: 4
   - Memory: 6GB
   - Swap: 2GB
   - Disk image size: 60GB

2. **플랫폼 지정**:
   모든 이미지에 `platform: linux/arm64` 명시

3. **메모리 할당**:
   - PostgreSQL: 2GB
   - OpenSearch: 2GB (Java heap)
   - Redis: 512MB
   - App: 1.5GB

### 캐싱 전략

- Redis TTL: 3600초 (1시간)
- 정적 파일: Nginx 캐싱
- 데이터베이스: Connection pooling

## 🔒 보안

### 방화벽 설정

```bash
# macOS 방화벽 규칙 추가
sudo pfctl -e
sudo pfctl -f /etc/pf.conf
```

### SSL/TLS (선택사항)

```bash
# Let's Encrypt 인증서 생성
./scripts/setup-ssl.sh

# 자체 서명 인증서 (개발용)
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout configs/nginx/ssl/private.key \
  -out configs/nginx/ssl/certificate.crt
```

## 🆘 문제 해결

### 일반적인 문제

1. **포트 충돌**:
   ```bash
   # 사용 중인 포트 확인
   lsof -i :5432
   lsof -i :6379
   lsof -i :9200
   ```

2. **메모리 부족**:
   ```bash
   # Docker 리소스 정리
   docker system prune -a
   docker volume prune
   ```

3. **서비스 시작 실패**:
   ```bash
   # 개별 서비스 재시작
   docker-compose -f docker-compose.prod.yml restart <service-name>
   ```

### 로그 위치

- 애플리케이션 (포그라운드): 콘솔 출력
- 애플리케이션 (백그라운드): `./logs/uvicorn.log`
- PostgreSQL: `docker logs kb-postgres-prod`
- OpenSearch: `docker logs kb-opensearch-prod`
- Redis: `docker logs kb-redis-prod`
- Nginx: `./logs/nginx/`

### 로그 관리

#### 백그라운드 모드 로그
`--background` 플래그로 실행 시:

```bash
# 실시간 로그 확인
tail -f logs/uvicorn.log

# 마지막 100줄 확인
tail -n 100 logs/uvicorn.log

# 오류 검색
grep ERROR logs/uvicorn.log

# 타임스탬프와 함께 확인
less logs/uvicorn.log
```

#### 깔끔한 출력 기능
시작 스크립트는 다음과 같이 깔끔하고 조직화된 출력을 제공합니다:
- Docker Compose 경고 억제
- Alembic 마이그레이션 메시지를 정보 수준으로 변환
- 구조화된 형식으로 로그 구성
- 명확한 상태 메시지 제공

## 📞 지원

문제가 발생하면:

1. 로그 확인: `./logs/` 디렉토리
2. 헬스체크: `http://localhost:8000/health`
3. 문서 참조: `docs/` 디렉토리
4. GitHub Issues 확인

---

**최종 업데이트**: 2025-08-21