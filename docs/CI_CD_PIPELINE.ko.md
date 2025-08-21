# CI/CD 파이프라인 문서

## 📚 Knowledge Database - GitHub Actions 워크플로우

이 문서는 Knowledge Database 프로젝트의 CI/CD 파이프라인 구성을 상세히 설명합니다.

---

## 🎯 개요

프로젝트는 3개의 GitHub Actions 워크플로우를 통해 완전 자동화된 CI/CD 파이프라인을 구현합니다:

1. **deploy.yml** - 메인 프로덕션 파이프라인
2. **deploy-local.yml** - 로컬 개발 환경
3. **deploy-aws.yml** - AWS 배포 전용

---

## 📋 워크플로우 상세 설명

### 1. 메인 배포 파이프라인 (`deploy.yml`)

#### 목적
전체 소프트웨어 개발 생명주기를 관리하는 포괄적인 CI/CD 파이프라인

#### 트리거 이벤트
- **Push**: `main`, `production` 브랜치
- **Pull Request**: 열기, 동기화, 재열기
- **수동 실행**: workflow_dispatch (환경 선택 가능)

#### 환경 변수
```yaml
AWS_REGION: us-west-2
ECR_REPOSITORY: knowledge-database
ECS_CLUSTER: knowledge-database
TERRAFORM_VERSION: 1.6.0
```

#### 작업 구조

##### 1️⃣ 코드 품질 및 보안 (Code Quality & Security)
**목적**: 코드 품질 검증 및 보안 취약점 스캔

**단계**:
- Python 3.11 환경 설정
- 의존성 설치
- 코드 포맷팅 검사 (black, isort)
- Linting (flake8)
- 타입 체킹 (mypy)
- 보안 스캔 (Bandit)
- 의존성 취약점 검사 (Safety)

**산출물**:
- `bandit-report.json`
- `safety-report.json`

##### 2️⃣ 테스트 (Test)
**목적**: 단위 및 통합 테스트 실행

**서비스 컨테이너**:
- PostgreSQL (pgvector 확장)
- Redis

**환경 변수**:
```yaml
DATABASE_URL: postgresql://testuser:testpass@localhost:5432/testdb
REDIS_URL: redis://localhost:6379
JWT_SECRET: test-jwt-secret
```

**메트릭**:
- 코드 커버리지: 최소 84.9%
- 테스트 결과 Codecov 업로드

##### 3️⃣ 빌드 및 푸시 (Build & Push)
**목적**: Docker 이미지 빌드 및 ECR 푸시

**단계**:
1. 환경 결정 (production/staging/dev)
2. AWS 자격 증명 구성
3. ECR 로그인
4. Docker Buildx 설정
5. 이미지 빌드 및 태그
   - 브랜치 이름
   - SHA 해시
   - 환경별 태그
6. ECR로 푸시
7. Trivy 취약점 스캔
8. SARIF 형식 보안 리포트 업로드

**캐싱**: GitHub Actions 캐시 사용

##### 4️⃣ ECS 배포 (Deploy to ECS)
**목적**: ECS Fargate에 애플리케이션 배포

**환경 매핑**:
- `production` 브랜치 → 프로덕션 환경
- `main` 브랜치 → 스테이징 환경
- 기타 → 개발 환경

**배포 프로세스**:
1. 태스크 정의 다운로드
2. 새 이미지로 태스크 정의 업데이트
3. ECS 서비스 업데이트
4. 서비스 안정성 대기
5. 데이터베이스 마이그레이션 실행
6. 헬스 체크 검증
7. Slack 알림 전송

##### 5️⃣ 인프라 업데이트 (Infrastructure Updates)
**목적**: Terraform을 통한 인프라 관리

**조건**: 수동 실행 시에만 활성화

**프로세스**:
1. Terraform 초기화
2. 계획 생성
3. 변경사항 적용 (main/production 브랜치만)

**상태 관리**:
- S3 백엔드
- DynamoDB 잠금 테이블

##### 6️⃣ 롤백 (Rollback)
**목적**: 이전 버전으로 긴급 롤백

**프로세스**:
1. 이전 태스크 정의 리비전 확인
2. 서비스를 이전 리비전으로 업데이트
3. 안정성 대기
4. Slack 알림

---

### 2. 로컬 배포 (`deploy-local.yml`)

#### 목적
로컬 개발 환경을 위한 간소화된 파이프라인

#### 트리거 이벤트
- **Push**: `main`, `develop` 브랜치
- **Pull Request**: `main` 브랜치로
- **수동 실행**: workflow_dispatch

#### 작업

##### 테스트
- Python 3.11 설정
- SQLite 메모리 DB 사용
- 테스트 실행 및 커버리지 측정
- Codecov 업로드

##### 빌드
- Docker 이미지 빌드
- 아티팩트로 저장 (7일 보관)

##### 배포 알림
- 로컬 배포 준비 알림
- 배포 스크립트 안내

---

### 3. AWS 배포 (`deploy-aws.yml`)

#### 목적
태그 기반 프로덕션 배포 전용 워크플로우

#### 트리거 이벤트
- **태그**: `v*` 패턴
- **수동 실행**: 환경 선택 (staging/production)

#### 구성
```yaml
AWS_REGION: ap-northeast-2  # 한국 리전
ECR_REPOSITORY: knowledge-database
```

#### 보안
- OIDC를 통한 AWS 인증
- Role ARN 사용 (액세스 키 미사용)

#### 작업

##### 빌드 및 푸시
1. AWS 자격 증명 구성 (OIDC)
2. ECR 로그인
3. Docker 이미지 빌드
4. ECR 푸시 (SHA 태그 + latest)

##### 스테이징 배포
- 조건: staging 선택 또는 태그 생성
- ECS 서비스 강제 재배포
- 서비스 안정성 대기

##### 프로덕션 배포
- 조건: production 선택 AND 태그 존재
- 스테이징 성공 후 실행
- GitHub Release 자동 생성

---

## 🔐 필수 GitHub Secrets

### AWS 자격 증명
```
AWS_ACCESS_KEY_ID         # AWS 액세스 키
AWS_SECRET_ACCESS_KEY     # AWS 시크릿 키
AWS_ROLE_ARN             # OIDC용 IAM Role ARN
```

### 인프라
```
TF_STATE_BUCKET          # Terraform 상태 S3 버킷
TF_LOCK_TABLE           # Terraform 잠금 DynamoDB 테이블
PRIVATE_SUBNET_IDS      # 프라이빗 서브넷 ID (콤마 구분)
ECS_SECURITY_GROUP_ID   # ECS 태스크 보안 그룹
```

### 알림
```
SLACK_WEBHOOK           # Slack 알림 웹훅 (선택사항)
```

---

## 🚀 배포 전략

### 브랜치 전략
```
feature/* → 개발 환경
main      → 스테이징 환경  
production → 프로덕션 환경
v*        → 프로덕션 릴리스
```

### 배포 유형

#### 블루-그린 배포
- ECS 서비스 레벨에서 구현
- 실패 시 자동 롤백
- 무중단 배포 보장

#### 카나리 배포
- AWS CodeDeploy 통합 (선택사항)
- 트래픽 점진적 이동
- 메트릭 기반 자동 롤백

#### 롤링 업데이트
- ECS 기본 배포 전략
- 최소 정상 퍼센트: 100%
- 최대 퍼센트: 200%

---

## 📊 모니터링 및 알림

### 배포 메트릭
- 배포 성공률
- 평균 배포 시간
- 롤백 빈도
- 다운타임 추적

### 알림
- **Slack**: 배포 시작/완료/실패
- **이메일**: 중요 실패 알림
- **GitHub**: PR 상태 업데이트

### 헬스 체크
```bash
# 헬스 체크 엔드포인트
GET /health

# 예상 응답
{
  "status": "healthy",
  "version": "1.0.0",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

## 🔧 수동 작업

### 수동 배포 트리거
```bash
# GitHub CLI 사용
gh workflow run deploy.yml \
  -f environment=production
```

### 워크플로우 상태 확인
```bash
# 최근 실행 확인
gh run list --workflow=deploy.yml

# 특정 실행 로그 보기
gh run view <run-id> --log
```

### 실행 중인 워크플로우 취소
```bash
gh run cancel <run-id>
```

---

## 🔄 롤백 절차

### 자동 롤백
- ECS Circuit Breaker 활성화
- 헬스 체크 실패 시 자동 롤백
- 배포 실패 시 이전 버전 유지

### 수동 롤백
```bash
# 스크립트 사용
./scripts/rollback.sh production app

# AWS CLI 직접 사용
aws ecs update-service \
  --cluster knowledge-database-production \
  --service knowledge-database-production \
  --task-definition knowledge-database-production:PREVIOUS_REVISION
```

---

## 📈 성능 최적화

### 빌드 최적화
- Docker 레이어 캐싱
- GitHub Actions 캐시
- 멀티스테이지 빌드
- 병렬 작업 실행

### 배포 속도
- 평균 빌드 시간: ~5분
- 평균 배포 시간: ~10분
- 전체 파이프라인: ~20분

---

## 🛠️ 문제 해결

### 일반적인 문제

#### 1. ECR 로그인 실패
```bash
# 수동 로그인 테스트
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin \
  [ACCOUNT_ID].dkr.ecr.ap-northeast-2.amazonaws.com
```

#### 2. 태스크 정의 업데이트 실패
```bash
# 태스크 정의 검증
aws ecs describe-task-definition \
  --task-definition knowledge-database-production
```

#### 3. 헬스 체크 타임아웃
```bash
# 서비스 이벤트 확인
aws ecs describe-services \
  --cluster knowledge-database-production \
  --services knowledge-database-production \
  --query 'services[0].events[:10]'
```

---

## 📚 모범 사례

### 보안
- 시크릿은 절대 코드에 포함하지 않음
- OIDC 인증 우선 사용
- 최소 권한 원칙 적용
- 정기적인 의존성 업데이트

### 성능
- 병렬 작업 최대화
- 캐싱 적극 활용
- 불필요한 단계 제거
- 조건부 실행 활용

### 신뢰성
- 모든 배포에 헬스 체크
- 자동 롤백 구성
- 단계별 알림 설정
- 배포 로그 보관

---

## 🔗 관련 문서

- [AWS 배포 가이드](./AWS_DEPLOYMENT_GUIDE.ko.md)
- [로컬 배포 가이드](./deployment/LOCAL_DEPLOYMENT.ko.md)
- [배포 체크리스트](./deployment/DEPLOYMENT_CHECKLIST.ko.md)
- [문제 해결 가이드](./TROUBLESHOOTING.ko.md)

---

## 📝 버전 히스토리

| 버전 | 날짜 | 변경사항 |
|------|------|----------|
| 1.0.0 | 2025-08-21 | 최초 문서 작성 |

---

*이 문서는 Knowledge Database v1.0.0의 CI/CD 파이프라인 구현을 설명합니다*