# 프로덕션 배포 체크리스트

## 🚀 Knowledge Database - 프로덕션 배포 체크리스트

**프로젝트**: Knowledge Database 시스템  
**버전**: 1.0.0  
**배포 날짜**: ___________  
**배포 담당자**: ___________  
**환경**: AWS 프로덕션  

---

## 📋 배포 전 체크리스트

### 1. 코드 준비 상태
- [ ] 모든 코드가 main 브랜치에 병합됨
- [ ] 코드 리뷰 완료 및 승인됨
- [ ] 버전 태그 생성됨 (v1.0.0)
- [ ] CHANGELOG.md 업데이트됨
- [ ] 중요 보안 취약점 없음 (Snyk/Trivy 스캔 통과)

### 2. 테스트 검증
- [ ] 단위 테스트 통과 (커버리지: 84.9% ✓)
- [ ] 통합 테스트 통과 (96.9% 성공률 ✓)
- [ ] E2E 테스트 완료
- [ ] 성능 테스트 통과
- [ ] 보안 테스트 통과
- [ ] 부하 테스트 완료

### 3. 문서화
- [ ] API 문서 업데이트됨
- [ ] README.md 최신 상태
- [ ] 배포 가이드 검토됨
- [ ] 문제 해결 가이드 준비됨
- [ ] 운영 매뉴얼 준비됨
- [ ] 이중언어 문서 완성 (한국어/영어)

### 4. 인프라 사전 요구사항
- [ ] AWS 계정 접근 권한 확인됨
- [ ] IAM 역할 및 권한 구성됨
- [ ] 도메인 이름 구성됨 (해당하는 경우)
- [ ] SSL 인증서 준비됨
- [ ] 백업 전략 문서화됨
- [ ] 재해 복구 계획 수립됨

### 5. 구성 관리
- [ ] 프로덕션 환경 변수 준비됨
- [ ] AWS Secrets Manager에 시크릿 저장됨
- [ ] 데이터베이스 연결 문자열 확인됨
- [ ] API 키 및 토큰 보안 처리됨
- [ ] 기능 플래그 구성됨

---

## 🏗️ 배포 단계

### 1단계: 인프라 설정
- [ ] terraform.tfvars 구성 검토
- [ ] Terraform 계획 실행
  ```bash
  cd infrastructure/terraform/aws
  terraform plan -var-file=environments/production/terraform.tfvars
  ```
- [ ] Terraform 적용 (인프라 생성)
  ```bash
  terraform apply -var-file=environments/production/terraform.tfvars
  ```
- [ ] VPC 및 네트워킹 확인
- [ ] RDS PostgreSQL 실행 확인
- [ ] OpenSearch 클러스터 정상 상태 확인
- [ ] ElastiCache Redis 상태 확인
- [ ] S3 버킷 생성 확인
- [ ] CloudWatch 로그 그룹 확인

### 2단계: 데이터베이스 설정
- [ ] RDS 인스턴스 연결
- [ ] 데이터베이스 마이그레이션 실행
  ```bash
  ./scripts/deploy-aws.sh production migrate
  ```
- [ ] pgvector 확장 설치 확인
- [ ] 초기 관리자 사용자 생성
- [ ] 데이터베이스 스키마 확인
- [ ] 데이터베이스 연결 테스트

### 3단계: 애플리케이션 배포
- [ ] Docker 이미지 빌드
  ```bash
  docker build -t knowledge-database:v1.0.0 .
  ```
- [ ] ECR로 푸시
  ```bash
  ./scripts/deploy-aws.sh production push
  ```
- [ ] ECS Fargate에 배포
  ```bash
  ./scripts/deploy-aws.sh production deploy
  ```
- [ ] ECS 태스크 실행 확인
- [ ] 태스크 헬스 상태 확인
- [ ] 자동 확장 구성 확인

### 4단계: 로드 밸런서 및 네트워킹
- [ ] ALB 활성 상태 확인
- [ ] 헬스 체크 엔드포인트 테스트
  ```bash
  curl https://your-domain.com/health
  ```
- [ ] 대상 그룹 정상 상태 확인
- [ ] WAF 규칙 활성화 확인
- [ ] DNS 해결 테스트
- [ ] SSL 인증서 확인

### 5단계: 서비스 통합
- [ ] OpenSearch 연결 테스트
- [ ] Redis 캐싱 확인
- [ ] S3 파일 업로드 테스트
- [ ] 이메일 서비스 확인 (해당하는 경우)
- [ ] 외부 API 통합 테스트
- [ ] 한국어 처리 기능 확인

---

## 🔍 배포 후 검증

### 애플리케이션 상태
- [ ] 헬스 엔드포인트 응답 (200 OK)
- [ ] API 엔드포인트 접근 가능
- [ ] 인증 기능 작동
- [ ] 데이터베이스 쿼리 실행
- [ ] 검색 기능 작동
- [ ] 관리자 대시보드 접근 가능

### 성능 메트릭
- [ ] 응답 시간 < 500ms (p95)
- [ ] CPU 사용률 < 70%
- [ ] 메모리 사용률 < 80%
- [ ] 데이터베이스 연결 풀 정상
- [ ] 캐시 적중률 > 80%

### 모니터링 및 알림
- [ ] CloudWatch 대시보드 데이터 표시
- [ ] 중요 알림 구성 및 테스트됨
- [ ] 로그 집계 작동
- [ ] APM 메트릭 표시
- [ ] 오류 추적 작동

### 보안 검증
- [ ] HTTPS 강제 적용
- [ ] 보안 헤더 존재
- [ ] 속도 제한 활성화
- [ ] 입력 검증 작동
- [ ] JWT 인증 확인
- [ ] CORS 올바르게 구성됨

---

## 🔄 롤백 절차

### 문제 발견 시:
1. [ ] 문제 문서화
2. [ ] 이해관계자 알림
3. [ ] 롤백 실행:
   ```bash
   ./scripts/rollback.sh production app
   ```
4. [ ] 이전 버전 실행 확인
5. [ ] 스모크 테스트 실행
6. [ ] 사고 보고서 업데이트

---

## 📊 운영 개시 체크리스트

### 비즈니스 준비 상태
- [ ] 이해관계자 알림 완료
- [ ] 지원팀 브리핑 완료
- [ ] 사용자 커뮤니케이션 발송
- [ ] 교육 완료
- [ ] SLA 문서화

### 기술 승인
- [ ] 개발팀 승인
- [ ] QA팀 승인
- [ ] 보안팀 승인
- [ ] DevOps팀 승인
- [ ] 제품 책임자 승인

### 최종 단계
- [ ] 프로덕션 모니터링 활성화
- [ ] 알림 활성화
- [ ] 상태 페이지 업데이트
- [ ] 배포 아티팩트 보관
- [ ] 배포 후 검토 일정 수립

---

## 📝 배포 후 작업

### 1일차
- [ ] 오류율 모니터링
- [ ] 성능 메트릭 확인
- [ ] 사용자 피드백 검토
- [ ] 중요 이슈 해결

### 1주차
- [ ] 사용 패턴 분석
- [ ] 비용 메트릭 검토
- [ ] 자동 확장 최적화
- [ ] 문서 업데이트

### 1개월차
- [ ] 사후 분석 실시
- [ ] 최적화 계획 수립
- [ ] 보안 상태 검토
- [ ] 재해 복구 절차 업데이트

---

## 🚨 비상 연락처

| 역할 | 이름 | 연락처 | 에스컬레이션 |
|------|------|---------|--------------|
| DevOps 리드 | _______ | _______ | 1차 |
| 백엔드 리드 | _______ | _______ | 1차 |
| 데이터베이스 관리자 | _______ | _______ | 2차 |
| 보안 리드 | _______ | _______ | 필요시 |
| 제품 책임자 | _______ | _______ | 비즈니스 |

---

## ✅ 배포 승인

**배포 상태**: [ ] 성공 [ ] 부분 성공 [ ] 실패

**비고**: _________________________________________________

**배포자**: _________________ **날짜**: _____________

**승인자**: _________________ **날짜**: _____________

---

## 📚 참고 문서

- [AWS 배포 가이드](docs/AWS_DEPLOYMENT_GUIDE.ko.md)
- [문제 해결 가이드](docs/TROUBLESHOOTING.ko.md)
- [API 문서](docs/api/API_DOCUMENTATION.ko.md)
- [아키텍처 문서](docs/sdlc/knowledge-database/architecture.md)
- [롤백 절차](scripts/rollback.sh)
- [모니터링 대시보드](https://console.aws.amazon.com/cloudwatch/)

---

## 🎯 빠른 참조

### 주요 명령어
```bash
# 배포 상태 확인
./scripts/deploy-aws.sh production status

# 로그 확인
aws logs tail /ecs/knowledge-production --follow

# 서비스 재시작
aws ecs update-service --cluster knowledge-cluster \
  --service knowledge-service --force-new-deployment

# 긴급 롤백
./scripts/rollback.sh production app --emergency
```

### 중요 URL
- 애플리케이션: https://your-domain.com
- 헬스 체크: https://your-domain.com/health
- API 문서: https://your-domain.com/docs
- 관리자 패널: https://your-domain.com/admin

### 모니터링 링크
- [CloudWatch 대시보드](https://console.aws.amazon.com/cloudwatch/)
- [ECS 서비스](https://console.aws.amazon.com/ecs/)
- [RDS 콘솔](https://console.aws.amazon.com/rds/)
- [OpenSearch 도메인](https://console.aws.amazon.com/opensearch/)

---

*이 체크리스트는 프로덕션 배포 전에 반드시 완료되고 승인되어야 합니다.*
*버전: 1.0.0 | 최종 업데이트: 2025-08-21*