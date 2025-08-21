# 🔧 Knowledge Database 관리자 가이드

## 목차
1. [시스템 개요](#시스템-개요)
2. [사용자 관리](#사용자-관리)
3. [콘텐츠 관리](#콘텐츠-관리)
4. [시스템 구성](#시스템-구성)
5. [모니터링 및 분석](#모니터링-및-분석)
6. [백업 및 복구](#백업-및-복구)
7. [성능 튜닝](#성능-튜닝)
8. [보안 관리](#보안-관리)
9. [문제 해결](#문제-해결)

## 시스템 개요

### 아키텍처 구성 요소
- **애플리케이션 서버**: Gunicorn에서 실행되는 FastAPI
- **데이터베이스**: pgvector 확장이 있는 PostgreSQL
- **검색 엔진**: 전체 텍스트 및 벡터 검색을 위한 OpenSearch
- **캐시 레이어**: 세션 및 데이터 캐싱을 위한 Redis
- **로드 밸런서**: Nginx 리버스 프록시
- **컨테이너 플랫폼**: Docker Compose가 있는 Docker

### 액세스 수준
1. **Super Admin**: 전체 시스템 액세스
2. **Admin**: 사용자 및 콘텐츠 관리
3. **Moderator**: 콘텐츠 검토 및 승인
4. **Editor**: 콘텐츠 생성 및 편집
5. **Viewer**: 읽기 전용 액세스

## 사용자 관리

### 사용자 생성
```bash
# Admin API를 통해
POST /api/v1/admin/users
{
  "email": "user@example.com",
  "username": "johndoe",
  "role": "editor",
  "department": "Engineering"
}
```

### 대량 사용자 가져오기
1. 사용자 데이터가 있는 CSV 파일 준비
2. 관리자 패널 → 사용자 → 가져오기로 이동
3. CSV 파일 업로드
4. 검토 및 가져오기 확인
5. 사용자는 활성화 이메일을 받음

### 권한 관리
- **역할 할당**: 관리자 패널 → 사용자 → 편집 → 역할
- **부서 액세스**: 부서 기반 권한 구성
- **API 액세스**: API 토큰 생성 및 관리
- **속도 제한**: 사용자별 또는 역할별 제한 설정

### 사용자 활동 모니터링
- 로그인 히스토리 보기
- 콘텐츠 기여 추적
- API 사용 모니터링
- 활동 보고서 내보내기

## 콘텐츠 관리

### 콘텐츠 조정
1. **검토 대기열**: 관리자 패널 → 조정
2. **사용 가능한 작업**:
   - 게시 승인
   - 변경 요청
   - 이유와 함께 거부
   - 에스컬레이션을 위한 플래그

### 카테고리 관리
```python
# 카테고리 구조
- 기술
  ├── 소프트웨어 개발
  │   ├── 백엔드
  │   ├── 프론트엔드
  │   └── DevOps
  └── 데이터 사이언스
      ├── 머신 러닝
      └── 분석
```

### 대량 작업
- **콘텐츠 가져오기**: JSON, CSV, 마크다운 지원
- **데이터 내보내기**: 전체 또는 필터링된 내보내기
- **대량 업데이트**: 배치 카테고리 변경, 태그 업데이트
- **정리 작업**: 중복 제거, 깨진 링크 수정

### 콘텐츠 품질 관리
- 최소 콘텐츠 길이 설정
- 필수 메타데이터 필드 구성
- 표절 감지 활성화
- 승인 워크플로우 구현

## 시스템 구성

### 환경 변수
```bash
# 핵심 설정
APP_ENV=production
SECRET_KEY=your-secret-key
DATABASE_URL=postgresql://user:pass@localhost/kb
REDIS_URL=redis://localhost:6379
OPENSEARCH_URL=http://localhost:9200

# 성능
MAX_CONNECTIONS=100
WORKER_COUNT=4
REQUEST_TIMEOUT=30

# 보안
JWT_EXPIRY=3600
RATE_LIMIT=100
CORS_ORIGINS=https://your-domain.com
```

### 데이터베이스 구성
```sql
-- PostgreSQL 최적화
ALTER SYSTEM SET shared_buffers = '2GB';
ALTER SYSTEM SET effective_cache_size = '6GB';
ALTER SYSTEM SET maintenance_work_mem = '512MB';
ALTER SYSTEM SET random_page_cost = 1.1;
```

### 검색 엔진 튜닝
```json
// OpenSearch 설정
{
  "index": {
    "number_of_shards": 3,
    "number_of_replicas": 1,
    "refresh_interval": "30s"
  },
  "analysis": {
    "analyzer": {
      "korean_analyzer": {
        "type": "custom",
        "tokenizer": "nori_tokenizer"
      }
    }
  }
}
```

## 모니터링 및 분석

### 시스템 메트릭
- **대시보드 URL**: http://localhost:3000/grafana
- **주요 메트릭**:
  - 요청 속도 및 지연 시간
  - 데이터베이스 쿼리 성능
  - 캐시 적중률
  - 검색 응답 시간
  - 오류율

### 애플리케이션 로그
```bash
# 애플리케이션 로그 보기
docker logs kb-app-prod -f

# 특정 오류 검색
docker logs kb-app-prod 2>&1 | grep ERROR

# 로그 내보내기
docker logs kb-app-prod > app_logs_$(date +%Y%m%d).log
```

### 사용 분석
- 가장 많이 검색된 용어
- 인기 콘텐츠
- 사용자 참여 메트릭
- 콘텐츠 생성 추세
- API 사용 패턴

### 알림 구성
```yaml
# 알림 규칙 (Prometheus)
groups:
  - name: knowledge_db
    rules:
      - alert: HighErrorRate
        expr: rate(errors_total[5m]) > 0.05
      - alert: DatabaseDown
        expr: up{job="postgresql"} == 0
      - alert: LowDiskSpace
        expr: disk_free_percent < 10
```

## 백업 및 복구

### 자동 백업
```bash
# 일일 백업 스크립트
#!/bin/bash
BACKUP_DIR="/backups/$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# 데이터베이스 백업
pg_dump -h localhost -U kb_user knowledge_db > $BACKUP_DIR/database.sql

# OpenSearch 스냅샷
curl -X PUT "localhost:9200/_snapshot/backup/$(date +%Y%m%d)?wait_for_completion=true"

# Redis 백업
redis-cli BGSAVE
cp /var/lib/redis/dump.rdb $BACKUP_DIR/

# 압축 및 암호화
tar -czf $BACKUP_DIR.tar.gz $BACKUP_DIR
gpg --encrypt --recipient admin@example.com $BACKUP_DIR.tar.gz
```

### 복구 절차
1. **데이터베이스 복구**:
   ```bash
   psql -h localhost -U kb_user knowledge_db < backup.sql
   ```

2. **검색 인덱스 복구**:
   ```bash
   curl -X POST "localhost:9200/_snapshot/backup/20250821/_restore"
   ```

3. **전체 시스템 복구**:
   - 모든 서비스 중지
   - 데이터베이스 복원
   - 검색 인덱스 복원
   - Redis 데이터 복원
   - 서비스 재시작
   - 기능 확인

## 성능 튜닝

### 데이터베이스 최적화
- **인덱싱 전략**:
  ```sql
  CREATE INDEX idx_items_created ON knowledge_items(created_at);
  CREATE INDEX idx_items_category ON knowledge_items(category_id);
  CREATE INDEX idx_search_vector ON knowledge_items USING ivfflat (embedding);
  ```

- **쿼리 최적화**:
  - 느린 쿼리에 EXPLAIN ANALYZE 사용
  - 쿼리 결과 캐싱 구현
  - JOIN 작업 최적화
  - 정기적인 VACUUM 및 ANALYZE

### 캐싱 전략
```python
# Redis 캐싱 구성
CACHE_TTL = {
    'search_results': 300,  # 5분
    'user_sessions': 3600,  # 1시간
    'static_content': 86400, # 24시간
    'api_responses': 60     # 1분
}
```

### 리소스 스케일링
- **수평 스케일링**: 더 많은 애플리케이션 컨테이너 추가
- **수직 스케일링**: 메모리/CPU 할당 증가
- **로드 밸런싱**: Nginx 업스트림 서버 구성
- **CDN 통합**: 정적 자산 오프로드

## 보안 관리

### 보안 체크리스트
- [ ] 강력한 비밀번호 시행
- [ ] 2단계 인증 활성화
- [ ] SSL/TLS 인증서 유효
- [ ] 정기적인 보안 업데이트 적용
- [ ] 방화벽 규칙 구성
- [ ] 속도 제한 활성
- [ ] 입력 유효성 검사 활성화
- [ ] SQL 인젝션 방지
- [ ] XSS 보호 구성
- [ ] CORS 적절히 설정

### 액세스 제어
```python
# 역할 기반 권한
PERMISSIONS = {
    'super_admin': ['*'],
    'admin': ['user:*', 'content:*', 'analytics:view'],
    'moderator': ['content:review', 'content:approve'],
    'editor': ['content:create', 'content:edit', 'content:delete'],
    'viewer': ['content:view', 'search:*']
}
```

### 감사 로깅
- 모든 관리자 작업 기록
- 사용자 인증 이벤트
- 콘텐츠 수정 추적
- API 액세스 기록
- 보안 이벤트 모니터링

## 문제 해결

### 일반적인 문제

#### 높은 메모리 사용량
```bash
# 메모리 사용량 확인
docker stats

# 특정 서비스 재시작
docker-compose restart opensearch

# 캐시 정리
redis-cli FLUSHDB
```

#### 느린 검색 성능
1. OpenSearch 클러스터 상태 확인
2. 인덱스 설정 최적화
3. 쿼리 복잡성 검토
4. 필요시 힙 크기 증가

#### 데이터베이스 연결 문제
```bash
# 연결 테스트
psql -h localhost -U kb_user -d knowledge_db -c "SELECT 1"

# 연결 풀 확인
SELECT count(*) FROM pg_stat_activity;

# 유휴 연결 종료
SELECT pg_terminate_backend(pid) 
FROM pg_stat_activity 
WHERE state = 'idle' AND state_change < now() - interval '1 hour';
```

### 비상 절차

#### 시스템 복구
1. 서비스 상태 확인
2. 오류 로그 검토
3. 실패한 서비스 재시작
4. 데이터베이스 연결 확인
5. 검색 기능 테스트
6. 사용자 액세스 확인

#### 데이터 손상
1. 영향받은 서비스 중지
2. 최신 백업에서 복원
3. 데이터 무결성 확인
4. 필요시 검색 데이터 재색인
5. 손상된 캐시 정리

### 지원 에스컬레이션
1. **레벨 1**: 시스템 알림 및 모니터링
2. **레벨 2**: 관리팀 조사
3. **레벨 3**: 개발팀 참여
4. **긴급**: 비상 대응팀

---

**버전**: 1.0.0  
**최종 업데이트**: 2025-08-21  
**비상 연락처**: ops@your-domain.com  
**문서**: https://docs.your-domain.com