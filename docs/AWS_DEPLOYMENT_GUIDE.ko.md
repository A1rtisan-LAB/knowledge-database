# AWS 배포 가이드

## 📚 Knowledge Database - AWS 프로덕션 배포 가이드

이 가이드는 Knowledge Database 시스템을 AWS 클라우드 환경에 배포하는 완전한 절차를 제공합니다.

---

## 📋 목차

1. [사전 요구사항](#사전-요구사항)
2. [아키텍처 개요](#아키텍처-개요)
3. [초기 설정](#초기-설정)
4. [인프라 배포](#인프라-배포)
5. [애플리케이션 배포](#애플리케이션-배포)
6. [모니터링 설정](#모니터링-설정)
7. [보안 구성](#보안-구성)
8. [비용 최적화](#비용-최적화)
9. [문제 해결](#문제-해결)
10. [재해 복구](#재해-복구)

---

## 🔧 사전 요구사항

### 필수 도구
- **AWS CLI** v2.0 이상
- **Terraform** v1.5 이상
- **Docker** v20.10 이상
- **Git** v2.0 이상
- **jq** (JSON 처리용)

### AWS 계정 요구사항
- 관리자 권한을 가진 IAM 사용자
- 프로그래매틱 액세스 키 (Access Key ID & Secret)
- 충분한 서비스 할당량:
  - VPC: 5개
  - EIP: 10개
  - EC2 인스턴스: 20개
  - RDS 인스턴스: 10개

### 로컬 환경 설정
```bash
# AWS CLI 구성
aws configure
# AWS Access Key ID [None]: YOUR_ACCESS_KEY
# AWS Secret Access Key [None]: YOUR_SECRET_KEY
# Default region name [None]: ap-northeast-2
# Default output format [None]: json

# 자격 증명 확인
aws sts get-caller-identity
```

---

## 🏗️ 아키텍처 개요

### 시스템 구성도
```
┌─────────────────────────────────────────────┐
│                 사용자                       │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│            CloudFront (CDN)                  │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│     Application Load Balancer + WAF          │
│            (퍼블릭 서브넷)                    │
└─────────────────────────────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│          ECS Fargate 클러스터                │
│         (프라이빗 서브넷)                     │
│     ┌──────────┐  ┌──────────┐             │
│     │ Task 1   │  │ Task 2   │  ...        │
│     └──────────┘  └──────────┘             │
└─────────────────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        │             │             │
        ▼             ▼             ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│   RDS    │  │OpenSearch│  │  Redis   │
│PostgreSQL│  │ Cluster  │  │ Cluster  │
│(Multi-AZ)│  │ (3 nodes)│  │ (3 nodes)│
└──────────┘  └──────────┘  └──────────┘
   DB 서브넷     프라이빗      프라이빗
```

### 주요 구성 요소

#### 네트워킹
- **VPC**: 10.0.0.0/16 CIDR 블록
- **서브넷**:
  - 퍼블릭: 10.0.1.0/24, 10.0.2.0/24, 10.0.3.0/24
  - 프라이빗: 10.0.10.0/24, 10.0.11.0/24, 10.0.12.0/24
  - 데이터베이스: 10.0.20.0/24, 10.0.21.0/24, 10.0.22.0/24
- **NAT Gateway**: 각 가용 영역에 1개
- **Internet Gateway**: VPC당 1개

#### 컴퓨팅
- **ECS Fargate**: 서버리스 컨테이너 실행
- **Auto Scaling**: 3-20 태스크 (CPU/메모리 기반)
- **Task 정의**: 2 vCPU, 4GB RAM

#### 데이터베이스
- **RDS PostgreSQL**: 
  - 엔진: PostgreSQL 15 + pgvector
  - 인스턴스: db.r6g.xlarge
  - 스토리지: 200GB gp3 (자동 확장)
  - 백업: 7일 보관, 자동 백업

#### 검색 엔진
- **Amazon OpenSearch**:
  - 버전: 2.11
  - 노드: 3개 (r6g.xlarge.search)
  - 스토리지: 각 200GB

#### 캐싱
- **ElastiCache Redis**:
  - 엔진: Redis 7.0
  - 노드: 3개 (cache.r6g.xlarge)
  - 복제: 활성화

---

## 🚀 초기 설정

### 1. 코드 저장소 클론
```bash
git clone https://github.com/your-org/knowledge-database.git
cd knowledge-database
```

### 2. 환경 변수 설정
```bash
# .env.production 파일 생성
cp .env.production.template .env.production

# 필수 값 설정
vim .env.production
```

### 3. Terraform 변수 구성
```bash
cd infrastructure/terraform/aws

# 프로덕션 변수 파일 생성
cp environments/production/terraform.tfvars.example terraform.tfvars

# 값 수정
vim terraform.tfvars
```

필수 변수:
```hcl
project_name    = "knowledge-database"
environment     = "production"
aws_region      = "ap-northeast-2"
domain_name     = "your-domain.com"
certificate_arn = "arn:aws:acm:..."
```

---

## 🏭 인프라 배포

### 1. Terraform 초기화
```bash
cd infrastructure/terraform/aws
terraform init
```

### 2. 배포 계획 검토
```bash
terraform plan -var-file=terraform.tfvars
```

### 3. 인프라 생성
```bash
# 자동 승인으로 배포
terraform apply -var-file=terraform.tfvars -auto-approve

# 또는 대화형 승인
terraform apply -var-file=terraform.tfvars
```

### 4. 출력 값 저장
```bash
# 중요 출력 값 저장
terraform output -json > outputs.json

# 주요 값 확인
terraform output alb_dns_name
terraform output rds_endpoint
terraform output opensearch_endpoint
```

---

## 📦 애플리케이션 배포

### 1. ECR 저장소 생성
```bash
# ECR 로그인
aws ecr get-login-password --region ap-northeast-2 | \
  docker login --username AWS --password-stdin \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.ap-northeast-2.amazonaws.com
```

### 2. Docker 이미지 빌드 및 푸시
```bash
# 프로덕션 이미지 빌드
docker build -t knowledge-database:latest \
  -f Dockerfile.production .

# 태그 지정
docker tag knowledge-database:latest \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.ap-northeast-2.amazonaws.com/knowledge-database:latest

# ECR로 푸시
docker push \
  $(aws sts get-caller-identity --query Account --output text).dkr.ecr.ap-northeast-2.amazonaws.com/knowledge-database:latest
```

### 3. 데이터베이스 마이그레이션
```bash
# RDS 연결 정보 가져오기
export DB_HOST=$(terraform output -raw rds_endpoint)
export DB_PASSWORD=$(aws secretsmanager get-secret-value \
  --secret-id knowledge-db-password \
  --query SecretString --output text)

# 마이그레이션 실행
./scripts/deploy-aws.sh production migrate
```

### 4. ECS 서비스 배포
```bash
# 서비스 업데이트
./scripts/deploy-aws.sh production deploy

# 배포 상태 확인
aws ecs describe-services \
  --cluster knowledge-cluster-production \
  --services knowledge-service \
  --query 'services[0].deployments'
```

---

## 📊 모니터링 설정

### CloudWatch 대시보드
```bash
# 대시보드 생성
aws cloudwatch put-dashboard \
  --dashboard-name knowledge-production \
  --dashboard-body file://monitoring/dashboard.json
```

### 주요 메트릭
- **애플리케이션**:
  - 요청 수 및 응답 시간
  - 오류율
  - 활성 연결 수
  
- **인프라**:
  - CPU 및 메모리 사용률
  - 네트워크 I/O
  - 디스크 사용률

- **데이터베이스**:
  - 연결 수
  - 쿼리 성능
  - 스토리지 사용량

### 알람 설정
```bash
# CPU 높음 알람
aws cloudwatch put-metric-alarm \
  --alarm-name knowledge-high-cpu \
  --alarm-description "CPU 사용률 80% 초과" \
  --metric-name CPUUtilization \
  --namespace AWS/ECS \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold
```

---

## 🔒 보안 구성

### 1. WAF 규칙
- SQL 인젝션 방지
- XSS 공격 차단
- 속도 제한 (분당 2000 요청)
- 지리적 차단 (필요시)

### 2. 보안 그룹
```bash
# 애플리케이션 보안 그룹
- 인바운드: ALB에서만 포트 8000
- 아웃바운드: HTTPS, 데이터베이스 포트

# 데이터베이스 보안 그룹
- 인바운드: 앱 보안 그룹에서만
- 아웃바운드: 제한됨
```

### 3. 암호화
- **전송 중**: TLS 1.2+ 강제
- **저장 시**: KMS 키로 암호화
- **백업**: 암호화된 스냅샷

### 4. 접근 제어
```bash
# IAM 역할 최소 권한 원칙
- ECS 태스크 역할: 필요한 AWS 서비스만
- RDS: IAM 데이터베이스 인증
- S3: 버킷 정책으로 제한
```

---

## 💰 비용 최적화

### 예상 월 비용
| 서비스 | 사양 | 예상 비용 |
|--------|------|-----------|
| ECS Fargate | 3 태스크 (2vCPU, 4GB) | $300 |
| RDS PostgreSQL | db.r6g.xlarge, 200GB | $400 |
| OpenSearch | 3x r6g.xlarge.search | $600 |
| ElastiCache | 3x cache.r6g.xlarge | $350 |
| ALB | 1개 + 데이터 전송 | $50 |
| 기타 | S3, CloudWatch, NAT | $110 |
| **총계** | | **~$1,810** |

### 비용 절감 전략
1. **Auto Scaling 최적화**
   ```bash
   # 야간 시간대 축소
   aws autoscaling put-scheduled-action \
     --scheduled-action-name scale-down-night \
     --min-size 1 --max-size 5
   ```

2. **예약 인스턴스**
   - RDS: 1년 예약시 30% 절감
   - ElastiCache: 1년 예약시 25% 절감

3. **S3 수명 주기**
   ```bash
   # 30일 후 IA로 이동
   aws s3api put-bucket-lifecycle-configuration \
     --bucket knowledge-logs \
     --lifecycle-configuration file://s3-lifecycle.json
   ```

---

## 🔧 문제 해결

### 일반적인 문제

#### 1. ECS 태스크 실패
```bash
# 로그 확인
aws logs tail /ecs/knowledge-production --follow

# 태스크 상태 확인
aws ecs describe-tasks \
  --cluster knowledge-cluster \
  --tasks $(aws ecs list-tasks --cluster knowledge-cluster --query 'taskArns[0]' --output text)
```

#### 2. 데이터베이스 연결 실패
```bash
# 보안 그룹 확인
aws ec2 describe-security-groups \
  --group-ids sg-xxxxx

# RDS 상태 확인
aws rds describe-db-instances \
  --db-instance-identifier knowledge-db
```

#### 3. 높은 레이턴시
```bash
# CloudFront 캐시 확인
aws cloudfront get-distribution-config \
  --id E1234567890ABC

# OpenSearch 성능 확인
curl -X GET "https://opensearch-endpoint/_cat/nodes?v"
```

### 디버깅 명령어
```bash
# ECS 실행 명령
aws ecs execute-command \
  --cluster knowledge-cluster \
  --task task-id \
  --container app \
  --interactive \
  --command "/bin/bash"

# 로그 스트림 확인
aws logs describe-log-streams \
  --log-group-name /ecs/knowledge \
  --order-by LastEventTime \
  --descending
```

---

## 🔄 재해 복구

### 백업 전략
1. **RDS 자동 백업**
   - 일일 자동 백업
   - 7일 보관
   - 특정 시점 복구 (PITR)

2. **OpenSearch 스냅샷**
   ```bash
   # S3로 스냅샷
   curl -X PUT "https://opensearch-endpoint/_snapshot/s3_backup/snapshot_1?wait_for_completion=true"
   ```

3. **애플리케이션 코드**
   - Git 저장소
   - ECR 이미지 버전 관리

### 복구 절차

#### RDS 복구
```bash
# 특정 시점으로 복구
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier knowledge-db \
  --target-db-instance-identifier knowledge-db-restored \
  --restore-time 2024-01-15T03:00:00.000Z
```

#### 전체 스택 복구
```bash
# Terraform 상태 복구
terraform refresh

# 인프라 재생성
terraform apply -var-file=terraform.tfvars

# 애플리케이션 재배포
./scripts/deploy-aws.sh production deploy
```

---

## 📚 추가 리소스

### 문서
- [API 문서](./docs/api/API_DOCUMENTATION.ko.md)
- [문제 해결 가이드](./docs/TROUBLESHOOTING.ko.md)
- [아키텍처 문서](./docs/ARCHITECTURE.ko.md)

### 모니터링 대시보드
- [CloudWatch](https://console.aws.amazon.com/cloudwatch/)
- [ECS 콘솔](https://console.aws.amazon.com/ecs/)
- [RDS 콘솔](https://console.aws.amazon.com/rds/)

### 지원
- 기술 지원: support@your-company.com
- 긴급 연락처: +82-XX-XXXX-XXXX
- Slack 채널: #knowledge-database-ops

---

## 🎯 체크리스트

배포 전 확인사항:
- [ ] AWS 자격 증명 구성됨
- [ ] Terraform 변수 설정됨
- [ ] 도메인 및 SSL 인증서 준비됨
- [ ] 백업 전략 수립됨
- [ ] 모니터링 알람 설정됨
- [ ] 보안 검토 완료됨
- [ ] 비용 예산 승인됨
- [ ] 롤백 계획 준비됨

---

*이 가이드는 Knowledge Database v1.0.0 기준으로 작성되었습니다.*
*최신 업데이트: 2025-08-21*