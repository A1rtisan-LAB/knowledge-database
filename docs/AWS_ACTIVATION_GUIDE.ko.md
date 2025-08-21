# AWS 배포 활성화 가이드

## 📚 개요

이 가이드는 Knowledge Database 프로젝트의 AWS 배포 워크플로우를 활성화하는 방법을 설명합니다. AWS 배포 기능은 현재 AWS 자격 증명 없이도 로컬 개발 및 테스트가 가능하도록 비활성화되어 있습니다.

---

## 🚀 빠른 시작

### 1단계: 워크플로우 활성화
```bash
# workflows 디렉토리로 이동
cd .github/workflows/

# AWS 워크플로우에서 .disabled 확장자 제거
mv deploy.yml.disabled deploy.yml
mv deploy-aws.yml.disabled deploy-aws.yml

# 변경사항 커밋 및 푸시
git add .
git commit -m "ci: AWS 배포 워크플로우 활성화"
git push
```

### 2단계: GitHub Secrets 설정
리포지토리 설정에서 다음 시크릿을 추가하세요:
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

기본 활성화는 여기까지입니다! 자세한 설정은 계속 읽어주세요.

---

## 📋 사전 요구사항

### 1. AWS 계정 설정
- 결제가 구성된 활성 AWS 계정
- AWS 서비스(ECS, RDS, S3)에 대한 기본 이해
- 예상 비용: 프로덕션 환경 월 ~$1,810

### 2. 필수 도구
- AWS CLI v2.x
- Terraform >= 1.5.0
- Docker >= 20.x

### 3. 로컬 환경
```bash
# AWS CLI 설치
curl "https://awscli.amazonaws.com/awscli-exe-linux-x86_64.zip" -o "awscliv2.zip"
unzip awscliv2.zip
sudo ./aws/install

# AWS CLI 구성
aws configure
```

---

## 🔐 GitHub Secrets 구성

### 필수 시크릿

**Settings → Secrets and variables → Actions**로 이동

#### 1. AWS 자격 증명 (필수)
| 시크릿 이름 | 설명 | 획득 방법 |
|------------|------|----------|
| `AWS_ACCESS_KEY_ID` | AWS 액세스 키 식별자 | IAM → 사용자 → 보안 자격 증명 → 액세스 키 생성 |
| `AWS_SECRET_ACCESS_KEY` | AWS 시크릿 액세스 키 | 액세스 키 ID와 함께 생성됨 |

#### 2. 인프라 시크릿 (Terraform에 필수)
| 시크릿 이름 | 설명 | 예시 값 |
|------------|------|---------|
| `TF_STATE_BUCKET` | Terraform 상태용 S3 버킷 | `my-terraform-state-bucket` |
| `TF_LOCK_TABLE` | 상태 잠금용 DynamoDB 테이블 | `terraform-state-lock` |

#### 3. 네트워크 구성 (ECS에 필수)
| 시크릿 이름 | 설명 | 예시 값 |
|------------|------|---------|
| `PRIVATE_SUBNET_IDS` | 프라이빗 서브넷 ID (쉼표로 구분) | `subnet-abc123,subnet-def456` |
| `ECS_SECURITY_GROUP_ID` | ECS 태스크용 보안 그룹 | `sg-abc12345` |

#### 4. 선택적 시크릿
| 시크릿 이름 | 설명 | 예시 값 |
|------------|------|---------|
| `SLACK_WEBHOOK` | Slack 알림 | `https://hooks.slack.com/...` |
| `AWS_ROLE_ARN` | OIDC 인증용 | `arn:aws:iam::123456789012:role/...` |

---

## 🏗️ AWS 인프라 설정

### 1단계: IAM 사용자 생성

```bash
# 프로그래매틱 액세스로 IAM 사용자 생성
aws iam create-user --user-name github-actions-user

# 관리자 정책 연결 (또는 사용자 정의 정책)
aws iam attach-user-policy \
  --user-name github-actions-user \
  --policy-arn arn:aws:iam::aws:policy/AdministratorAccess

# 액세스 키 생성
aws iam create-access-key --user-name github-actions-user
```

### 2단계: Terraform 상태용 S3 버킷 생성

```bash
# S3 버킷 생성
aws s3 mb s3://knowledge-db-terraform-state-$(date +%s)

# 버전 관리 활성화
aws s3api put-bucket-versioning \
  --bucket knowledge-db-terraform-state-$(date +%s) \
  --versioning-configuration Status=Enabled
```

### 3단계: 상태 잠금용 DynamoDB 테이블 생성

```bash
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

### 4단계: Terraform으로 인프라 배포

```bash
# Terraform 디렉토리로 이동
cd infrastructure/terraform/aws

# Terraform 초기화
terraform init

# 계획 검토
terraform plan

# 인프라 적용
terraform apply
```

---

## 🔄 워크플로우 활성화

### 사용 가능한 워크플로우

#### 1. `deploy.yml` - 메인 CI/CD 파이프라인
- **트리거**: main/production 브랜치로 푸시
- **기능**: 코드 품질, 테스트, Docker 빌드, ECS 배포
- **필수 시크릿**: 모든 AWS 및 인프라 시크릿

#### 2. `deploy-aws.yml` - 태그 기반 배포
- **트리거**: 버전 태그 (v*)
- **기능**: 릴리스 생성을 포함한 프로덕션 배포
- **리전**: ap-northeast-2 (서울)

### 활성화 단계

1. **.disabled 확장자 제거**:
   ```bash
   mv deploy.yml.disabled deploy.yml
   ```

2. **워크플로우 문법 검증**:
   ```bash
   # act로 로컬 테스트 (선택사항)
   brew install act
   act -l
   ```

3. **수동 트리거로 테스트**:
   - GitHub의 Actions 탭으로 이동
   - 워크플로우 선택
   - "Run workflow" 클릭

---

## 🧪 설정 테스트

### 1. AWS 자격 증명 검증
```bash
aws sts get-caller-identity
```

### 2. GitHub Secrets 테스트
테스트 워크플로우 생성 (`.github/workflows/test-secrets.yml`):
```yaml
name: AWS Secrets 테스트
on: workflow_dispatch
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: AWS 자격 증명 확인
        env:
          AWS_ACCESS_KEY_ID: ${{ secrets.AWS_ACCESS_KEY_ID }}
          AWS_SECRET_ACCESS_KEY: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
        run: |
          if [ -n "$AWS_ACCESS_KEY_ID" ]; then
            echo "✅ AWS 자격 증명이 구성되었습니다"
          else
            echo "❌ AWS 자격 증명이 누락되었습니다"
          fi
```

### 3. 인프라 확인
```bash
# ECS 클러스터 확인
aws ecs list-clusters

# RDS 인스턴스 확인
aws rds describe-db-instances

# S3 버킷 확인
aws s3 ls
```

---

## 💰 비용 추정

### 월간 비용 (프로덕션)
| 서비스 | 구성 | 예상 비용 |
|--------|------|----------|
| ECS Fargate | 3개 태스크 (2vCPU, 4GB) | $300 |
| RDS PostgreSQL | db.r6g.xlarge | $400 |
| OpenSearch | 3노드 클러스터 | $600 |
| ElastiCache | Redis 클러스터 | $350 |
| Load Balancer | Application LB | $50 |
| 기타 | S3, CloudWatch, NAT | $110 |
| **합계** | | **월 ~$1,810** |

### 비용 최적화 팁
- 비프로덕션 환경에서 스팟 인스턴스 사용
- 사용량 기반 자동 스케일링 활성화
- 예측 가능한 워크로드에 예약 인스턴스 사용
- S3 수명 주기 정책 구현

---

## 🚨 문제 해결

### 일반적인 문제

#### 1. 워크플로우가 트리거되지 않음
- 파일에 `.disabled` 확장자가 있는지 확인
- 브랜치 보호 규칙 확인
- `act`로 워크플로우 문법 확인

#### 2. AWS 인증 실패
```yaml
Error: Could not assume role
```
**해결책**: AWS_ACCESS_KEY_ID와 AWS_SECRET_ACCESS_KEY가 올바르게 설정되었는지 확인

#### 3. Terraform 상태 잠금 오류
```
Error acquiring the state lock
```
**해결책**: 
```bash
# 강제 잠금 해제 (주의해서 사용)
terraform force-unlock <lock-id>
```

#### 4. ECS 태스크 시작 실패
- CloudWatch 로그 확인
- 보안 그룹 규칙 확인
- ECR에 Docker 이미지가 있는지 확인

---

## 📚 추가 리소스

### 문서
- [AWS 배포 가이드](./AWS_DEPLOYMENT_GUIDE.ko.md)
- [CI/CD 파이프라인 문서](./CI_CD_PIPELINE.ko.md)
- [문제 해결 가이드](./TROUBLESHOOTING.ko.md)

### AWS 문서
- [ECS 모범 사례](https://docs.aws.amazon.com/AmazonECS/latest/bestpracticesguide/)
- [PostgreSQL을 사용한 RDS](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/)
- [Terraform AWS 프로바이더](https://registry.terraform.io/providers/hashicorp/aws/)

---

## 🤝 지원

문제가 발생하면:
1. 문제 해결 섹션 확인
2. GitHub Actions 로그 검토
3. 리포지토리에 이슈 생성
4. 개발 팀에 문의

---

## ✅ 체크리스트

AWS 배포를 활성화하기 전에:
- [ ] AWS 계정이 활성 상태
- [ ] 필요한 권한으로 IAM 사용자 생성됨
- [ ] GitHub Secrets 구성됨
- [ ] Terraform 상태 버킷 생성됨
- [ ] DynamoDB 잠금 테이블 생성됨
- [ ] 워크플로우 활성화됨 (.disabled 제거됨)
- [ ] 테스트 배포 성공

---

*최종 업데이트: 2025-08-21*