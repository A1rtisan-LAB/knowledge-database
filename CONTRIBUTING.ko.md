# Knowledge Database 기여 가이드

먼저 Knowledge Database에 기여를 고려해 주셔서 감사합니다! 여러분 같은 분들이 Knowledge Database를 훌륭한 도구로 만들어 주십니다.

## 행동 강령

이 프로젝트에 참여함으로써 다음과 같은 행동 강령을 준수해 주시기 바랍니다:
- 존중하고 포용적인 태도를 유지하세요
- 새로운 참여자를 환영하고 시작을 도와주세요
- 커뮤니티에 최선인 것에 집중하세요
- 다른 커뮤니티 구성원에게 공감을 표현하세요

## 어떻게 기여할 수 있나요?

### 버그 보고

버그 리포트를 작성하기 전에, 이미 존재하는 이슈를 확인해 주세요. 버그 리포트를 작성할 때는 가능한 한 많은 세부 정보를 포함해 주세요:

- **명확하고 설명적인 제목 사용**
- **문제를 재현하는 정확한 단계 설명**
- **단계를 시연하는 구체적인 예제 제공**
- **관찰된 동작과 예상된 동작 설명**
- **가능하면 스크린샷 포함**
- **환경 세부사항 포함** (OS, Python 버전, Docker 버전)

### 개선 제안

개선 제안은 GitHub 이슈로 추적됩니다. 개선 제안을 작성할 때는 다음을 포함해 주세요:

- **명확하고 설명적인 제목 사용**
- **제안된 개선 사항의 자세한 설명 제공**
- **이 개선이 왜 유용한지 설명**
- **고려한 대안 솔루션 나열**

### 첫 번째 코드 기여

어디서부터 시작해야 할지 모르겠다면 다음 이슈들을 살펴보세요:
- `good first issue` - 몇 줄의 코드만 필요한 이슈
- `help wanted` - 추가 관심이 필요한 이슈

### Pull Request

1. 저장소를 포크하고 `main`에서 브랜치를 생성하세요
2. 테스트가 필요한 코드를 추가했다면 테스트를 추가하세요
3. API를 변경했다면 문서를 업데이트하세요
4. 테스트 스위트가 통과하는지 확인하세요
5. 코드가 기존 코드 스타일을 따르는지 확인하세요
6. Pull Request를 제출하세요!

## 개발 프로세스

### 개발 환경 설정

```bash
# 포크 클론
git clone https://github.com/your-username/knowledge-database.git
cd knowledge-database

# 업스트림 원격 추가
git remote add upstream https://github.com/original/knowledge-database.git

# 가상 환경 생성
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 의존성 설치
pip install -r requirements.txt
pip install -r requirements-dev.txt

# pre-commit 훅 설정
pre-commit install

# 로컬에서 애플리케이션 실행
./scripts/start-local.sh
```

### 코드 스타일

코드 품질을 유지하기 위해 여러 도구를 사용합니다:

- **Black** - Python 코드 포매팅
- **isort** - import 정렬
- **flake8** - 린팅
- **mypy** - 타입 체킹

모든 검사 실행:
```bash
# 코드 포맷
black app/ tests/
isort app/ tests/

# 린팅 실행
flake8 app/ tests/
mypy app/

# 또는 한 번에 모두 실행
make lint
```

### 테스팅

새로운 기능에 대한 테스트를 작성하세요:

```bash
# 모든 테스트 실행
pytest

# 커버리지와 함께 실행
pytest --cov=app --cov-report=html

# 특정 테스트 파일 실행
pytest tests/unit/test_auth.py

# 병렬로 테스트 실행
pytest -n auto
```

### 커밋 메시지

[Conventional Commits](https://www.conventionalcommits.org/) 명세를 따릅니다:

- `feat:` 새로운 기능
- `fix:` 버그 수정
- `docs:` 문서 변경
- `style:` 코드 스타일 변경 (포매팅 등)
- `refactor:` 코드 리팩토링
- `test:` 테스트 추가 또는 변경
- `chore:` 유지보수 작업

예시:
```
feat: 검색에 한국어 지원 추가
fix: JWT 토큰 만료 문제 해결
docs: v2 엔드포인트 API 문서 업데이트
```

### 문서화

- 필요한 경우 README.md 업데이트
- 모든 공개 함수와 클래스에 docstring 추가
- 엔드포인트 변경 시 API 문서 업데이트
- 영어와 한국어 문서를 동기화 상태로 유지

### 브랜치 명명 규칙

- `feature/` - 새 기능 (예: `feature/add-export-api`)
- `fix/` - 버그 수정 (예: `fix/search-pagination`)
- `docs/` - 문서 업데이트 (예: `docs/update-api-guide`)
- `refactor/` - 코드 리팩토링 (예: `refactor/optimize-queries`)

## 리뷰 프로세스

1. **자동 검사**: 모든 PR은 다음을 통과해야 합니다:
   - 단위 테스트
   - 통합 테스트
   - 코드 스타일 검사
   - 보안 스캐닝

2. **코드 리뷰**: 최소 한 명의 메인테이너 리뷰 필요
   - 코드 품질
   - 성능 영향
   - 보안 고려사항
   - 문서 완성도

3. **테스팅**: UI 변경 사항에 대한 수동 테스트

## 릴리스 프로세스

1. `VERSION` 파일의 버전 업데이트
2. CHANGELOG.md 업데이트
3. 릴리스 PR 생성
4. 병합 후 릴리스 태그
5. 스테이징 배포
6. 프로덕션 배포

## 커뮤니티

- **Discord**: [Discord 참여](https://discord.gg/knowledge-db)
- **포럼**: [커뮤니티 포럼](https://forum.knowledge-db.com)
- **Twitter**: [@KnowledgeDB](https://twitter.com/knowledgedb)

## 인정

기여자는 다음에서 인정받습니다:
- CHANGELOG.md
- GitHub 기여자 페이지
- 프로젝트 문서

## 질문이 있으신가요?

자유롭게 연락주세요:
- 질문을 위한 이슈 열기
- Discord에서 연락
- contribute@knowledge-db.com으로 메인테이너에게 이메일

기여해 주셔서 감사합니다! 🎉