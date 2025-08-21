# Knowledge Database API 문서

## 목차
- [개요](#개요)
- [기본 URL](#기본-url)
- [인증](#인증)
- [속도 제한](#속도-제한)
- [오류 처리](#오류-처리)
- [페이지네이션](#페이지네이션)
- [API 엔드포인트](#api-엔드포인트)
  - [루트 엔드포인트](#루트-엔드포인트)
  - [인증](#인증-엔드포인트)
  - [지식 항목](#지식-항목)
  - [카테고리](#카테고리)
  - [검색](#검색)
  - [분석](#분석)
  - [관리자](#관리자)

## 개요

Knowledge Database API는 AI 기반 검색 기능과 이중 언어(영어/한국어) 지원을 갖춘 조직 지식 관리를 위한 포괄적인 RESTful API입니다. FastAPI로 구축되어 자동 OpenAPI 문서화, 강력한 인증 및 엔터프라이즈급 보안 기능을 제공합니다.

### 주요 기능
- JWT 기반 인증 및 리프레시 토큰
- 역할 기반 접근 제어(RBAC)
- 다국어 지원(영어 및 한국어)
- OpenSearch를 사용한 AI 기반 의미 검색
- 실시간 분석 및 메트릭
- 속도 제한 및 요청 조절
- 포괄적인 감사 로깅

## 기본 URL

```
프로덕션: https://api.knowledge.example.com/api/v1
개발: http://localhost:8000/api/v1
```

## 인증

API는 JWT(JSON Web Token) Bearer 인증을 사용합니다. 대부분의 엔드포인트는 인증이 필요합니다.

### 인증 플로우

1. **로그인**: `/auth/login`에 자격 증명으로 POST하여 액세스 및 리프레시 토큰 수신
2. **액세스 토큰 사용**: Authorization 헤더에 포함: `Authorization: Bearer <access_token>`
3. **토큰 갱신**: 액세스 토큰 만료 시 리프레시 토큰으로 새 토큰 획득
4. **로그아웃**: `/auth/logout`에 POST하여 세션 무효화

### 토큰 만료 시간
- 액세스 토큰: 30분
- 리프레시 토큰: 7일

### 사용자 역할
- `viewer`: 게시된 콘텐츠에 대한 읽기 전용 액세스
- `editor`: 콘텐츠 생성, 편집 및 게시 가능
- `admin`: 사용자 관리를 포함한 전체 시스템 액세스

### Authorization 헤더

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## 속도 제한

API는 남용을 방지하기 위해 속도 제한을 구현합니다:

- **기본 제한**: 사용자당 60초당 100개 요청
- **버스트 제한**: 초당 최대 10개 요청
- **반환되는 헤더**:
  - `X-RateLimit-Limit`: 허용된 최대 요청 수
  - `X-RateLimit-Remaining`: 현재 창에서 남은 요청 수
  - `X-RateLimit-Reset`: 제한이 재설정되는 Unix 타임스탬프

### 속도 제한 응답

```json
{
  "error": "rate_limit_exceeded",
  "message": "속도 제한을 초과했습니다. 나중에 다시 시도해주세요.",
  "retry_after": 45
}
```

## 오류 처리

API는 적절한 HTTP 상태 코드와 함께 일관된 오류 응답을 반환합니다.

### 오류 응답 형식

```json
{
  "error": "error_code",
  "message": "사람이 읽을 수 있는 오류 메시지",
  "details": {
    "field": "오류에 대한 추가 컨텍스트"
  }
}
```

### 일반적인 HTTP 상태 코드

| 상태 코드 | 설명 |
|----------|------|
| 200 | OK - 요청 성공 |
| 201 | Created - 리소스 생성 성공 |
| 204 | No Content - 요청 성공, 반환 내용 없음 |
| 400 | Bad Request - 잘못된 요청 매개변수 |
| 401 | Unauthorized - 인증 필요 또는 유효하지 않음 |
| 403 | Forbidden - 권한 부족 |
| 404 | Not Found - 리소스를 찾을 수 없음 |
| 409 | Conflict - 리소스가 이미 존재함 |
| 422 | Unprocessable Entity - 유효성 검사 오류 |
| 429 | Too Many Requests - 속도 제한 초과 |
| 500 | Internal Server Error - 서버 오류 |

## 페이지네이션

목록 엔드포인트는 쿼리 매개변수를 사용한 페이지네이션을 지원합니다:

### 페이지네이션 매개변수

| 매개변수 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `page` | integer | 1 | 페이지 번호 (1부터 시작) |
| `limit` | integer | 20 | 페이지당 항목 수 (최대 100) |

### 페이지네이션 응답 형식

```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "limit": 20,
  "has_more": true
}
```

## API 엔드포인트

### 루트 엔드포인트

#### GET /
API 정보 가져오기

**응답:**
```json
{
  "name": "Knowledge Database API",
  "version": "1.0.0",
  "status": "healthy",
  "docs": "/docs"
}
```

#### GET /health
모니터링을 위한 헬스 체크 엔드포인트

**응답:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production"
}
```

### 인증 엔드포인트

#### POST /auth/login
사용자 인증 및 토큰 수신

**요청 본문:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "organization_slug": "optional-org-slug"
}
```

**응답:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "role": "editor",
    "organization_id": "660e8400-e29b-41d4-a716-446655440001",
    "is_active": true,
    "is_verified": true,
    "last_login_at": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-01T00:00:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

#### POST /auth/refresh
리프레시 토큰을 사용하여 액세스 토큰 갱신

**요청 본문:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**응답:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer"
}
```

#### POST /auth/logout
현재 사용자 로그아웃

**인증:** 필수

**응답:** 204 No Content

#### GET /auth/me
현재 사용자 정보 가져오기

**인증:** 필수

**응답:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "user@example.com",
  "username": "johndoe",
  "full_name": "John Doe",
  "role": "editor",
  "organization_id": "660e8400-e29b-41d4-a716-446655440001",
  "is_active": true,
  "is_verified": true,
  "last_login_at": "2024-01-15T10:30:00Z",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### 지식 항목

#### GET /knowledge
필터링 및 페이지네이션과 함께 지식 항목 목록 조회

**인증:** 선택사항 (인증되지 않은 사용자에게는 게시된 항목만 표시)

**쿼리 매개변수:**
| 매개변수 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `page` | integer | 아니오 | 페이지 번호 (기본값: 1) |
| `limit` | integer | 아니오 | 페이지당 항목 수 (1-100, 기본값: 20) |
| `category_id` | uuid | 아니오 | 카테고리 ID로 필터링 |
| `type` | string | 아니오 | 콘텐츠 유형으로 필터링 |
| `status` | string | 아니오 | 상태로 필터링 (편집자만) |
| `tags` | array[string] | 아니오 | 태그로 필터링 (모두 포함해야 함) |
| `language` | string | 아니오 | 언어 선호: en, ko (기본값: en) |
| `sort` | string | 아니오 | 정렬 기준: created_at, updated_at, title, views, helpful |
| `order` | string | 아니오 | 정렬 순서: asc, desc (기본값: desc) |

**응답:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "type": "article",
      "slug": "getting-started-guide",
      "category": {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "name_ko": "시작하기",
        "name_en": "Getting Started",
        "slug": "getting-started"
      },
      "title_ko": "시작 가이드",
      "title_en": "Getting Started Guide",
      "summary_ko": "플랫폼 사용을 시작하는 방법",
      "summary_en": "How to get started with our platform",
      "tags": ["tutorial", "beginner"],
      "status": "published",
      "version": 1,
      "view_count": 1250,
      "helpful_count": 89,
      "not_helpful_count": 5,
      "published_at": "2024-01-10T08:00:00Z",
      "created_at": "2024-01-09T10:00:00Z",
      "updated_at": "2024-01-10T08:00:00Z"
    }
  ],
  "total": 150,
  "page": 1,
  "limit": 20,
  "has_more": true
}
```

#### GET /knowledge/{id}
ID로 상세 지식 항목 가져오기

**인증:** 선택사항 (미게시 항목에는 필수)

**경로 매개변수:**
- `id` (uuid): 지식 항목 ID

**쿼리 매개변수:**
- `language` (string): 언어 선호: en, ko (기본값: en)
- `include_related` (boolean): 관련 항목 포함 (기본값: false)

**응답:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "article",
  "slug": "getting-started-guide",
  "category": {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "name_ko": "시작하기",
    "name_en": "Getting Started",
    "slug": "getting-started"
  },
  "title_ko": "시작 가이드",
  "title_en": "Getting Started Guide",
  "content_ko": "# 시작하기\n\n이 가이드는...",
  "content_en": "# Getting Started\n\nThis guide will...",
  "summary_ko": "플랫폼 사용을 시작하는 방법",
  "summary_en": "How to get started with our platform",
  "tags": ["tutorial", "beginner"],
  "status": "published",
  "version": 1,
  "view_count": 1251,
  "helpful_count": 89,
  "not_helpful_count": 5,
  "metadata": {
    "read_time": 5,
    "difficulty": "beginner"
  },
  "seo_title_ko": "시작 가이드 - Knowledge Base",
  "seo_title_en": "Getting Started Guide - Knowledge Base",
  "seo_description_ko": "우리 플랫폼 사용을 시작하는 완벽한 가이드",
  "seo_description_en": "Complete guide to getting started with our platform",
  "seo_keywords": ["tutorial", "guide", "getting started"],
  "related_items": [],
  "published_at": "2024-01-10T08:00:00Z",
  "created_at": "2024-01-09T10:00:00Z",
  "updated_at": "2024-01-10T08:00:00Z"
}
```

#### POST /knowledge
새 지식 항목 생성

**인증:** 필수 (편집자 역할)

**요청 본문:**
```json
{
  "type": "article",
  "slug": "new-feature-guide",
  "category_id": "770e8400-e29b-41d4-a716-446655440002",
  "title_ko": "새 기능 가이드",
  "title_en": "New Feature Guide",
  "content_ko": "# 새 기능\n\n이 기능은...",
  "content_en": "# New Feature\n\nThis feature...",
  "summary_ko": "새로운 기능에 대한 설명",
  "summary_en": "Description of the new feature",
  "tags": ["feature", "new"],
  "metadata": {
    "version": "2.0",
    "author": "John Doe"
  },
  "seo_title_ko": "새 기능 가이드",
  "seo_title_en": "New Feature Guide",
  "seo_description_ko": "새로운 기능 사용 방법",
  "seo_description_en": "How to use the new feature",
  "seo_keywords": ["feature", "guide"]
}
```

**응답:** 201 Created
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "type": "article",
  "slug": "new-feature-guide",
  ...
}
```

#### PUT /knowledge/{id}
지식 항목 업데이트

**인증:** 필수 (편집자 역할)

**경로 매개변수:**
- `id` (uuid): 지식 항목 ID

**요청 본문:** (모든 필드 선택사항)
```json
{
  "title_ko": "업데이트된 제목",
  "title_en": "Updated Title",
  "content_ko": "업데이트된 내용",
  "content_en": "Updated content",
  "tags": ["updated", "feature"]
}
```

**응답:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "article",
  ...
}
```

#### DELETE /knowledge/{id}
지식 항목 소프트 삭제

**인증:** 필수 (편집자 역할)

**경로 매개변수:**
- `id` (uuid): 지식 항목 ID

**응답:** 204 No Content

#### POST /knowledge/{id}/publish
지식 항목 게시

**인증:** 필수 (편집자 역할)

**경로 매개변수:**
- `id` (uuid): 지식 항목 ID

**응답:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "published",
  "published_at": "2024-01-15T12:00:00Z",
  ...
}
```

#### GET /knowledge/{id}/versions
지식 항목의 버전 기록 가져오기

**인증:** 필수

**경로 매개변수:**
- `id` (uuid): 지식 항목 ID

**응답:**
```json
[
  {
    "id": "990e8400-e29b-41d4-a716-446655440004",
    "version_number": 2,
    "title_ko": "업데이트된 가이드",
    "title_en": "Updated Guide",
    "change_summary": "고급 기능에 대한 새 섹션 추가",
    "created_at": "2024-01-12T10:00:00Z"
  },
  {
    "id": "aa0e8400-e29b-41d4-a716-446655440005",
    "version_number": 1,
    "title_ko": "원본 가이드",
    "title_en": "Original Guide",
    "change_summary": "초기 버전",
    "created_at": "2024-01-09T10:00:00Z"
  }
]
```

### 카테고리

#### GET /categories
계층 구조와 함께 카테고리 목록 조회

**인증:** 필수

**쿼리 매개변수:**
- `parent_id` (uuid): 부모 카테고리로 필터링 (루트 카테고리의 경우 null)
- `language` (string): 언어 선호: en, ko (기본값: en)

**응답:**
```json
[
  {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "parent_id": null,
    "name": "시작하기",
    "slug": "getting-started",
    "description": "초보자 가이드 및 튜토리얼",
    "icon": "book",
    "display_order": 1,
    "item_count": 15
  },
  {
    "id": "880e8400-e29b-41d4-a716-446655440003",
    "parent_id": null,
    "name": "고급 주제",
    "slug": "advanced",
    "description": "고급 기능 및 개념",
    "icon": "graduation-cap",
    "display_order": 2,
    "item_count": 23
  }
]
```

#### GET /categories/{id}
하위 카테고리와 함께 카테고리 상세 정보 가져오기

**인증:** 필수

**경로 매개변수:**
- `id` (uuid): 카테고리 ID

**쿼리 매개변수:**
- `language` (string): 언어 선호: en, ko (기본값: en)

**응답:**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "parent_id": null,
  "name": "시작하기",
  "slug": "getting-started",
  "description": "초보자 가이드 및 튜토리얼",
  "icon": "book",
  "display_order": 1,
  "item_count": 15,
  "children": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440004",
      "name": "설치",
      "slug": "installation",
      "item_count": 5
    },
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440005",
      "name": "구성",
      "slug": "configuration",
      "item_count": 10
    }
  ]
}
```

#### POST /categories
새 카테고리 생성

**인증:** 필수 (편집자 역할)

**요청 본문:**
```json
{
  "parent_id": null,
  "name_ko": "새 카테고리",
  "name_en": "New Category",
  "slug": "new-category",
  "description_ko": "새 카테고리 설명",
  "description_en": "New category description",
  "icon": "folder",
  "display_order": 3
}
```

**응답:** 201 Created
```json
{
  "id": "bb0e8400-e29b-41d4-a716-446655440006",
  "name_ko": "새 카테고리",
  "name_en": "New Category",
  "slug": "new-category",
  "parent_id": null
}
```

### 검색

#### POST /search
AI 기반 의미 검색으로 지식 베이스 검색

**인증:** 선택사항

**요청 본문:**
```json
{
  "query": "인증 구성 방법"
}
```

**쿼리 매개변수:**
- `language` (string): 언어: en, ko (기본값: en)
- `search_type` (string): 유형: keyword, semantic, hybrid (기본값: hybrid)
- `page` (integer): 페이지 번호 (기본값: 1)
- `limit` (integer): 페이지당 결과 수 (1-100, 기본값: 20)
- `category_ids` (array[string]): 카테고리 ID로 필터링
- `types` (array[string]): 콘텐츠 유형으로 필터링
- `tags` (array[string]): 태그로 필터링

**응답:**
```json
{
  "query": "인증 구성 방법",
  "total": 12,
  "page": 1,
  "limit": 20,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "인증 구성 가이드",
      "slug": "auth-configuration",
      "summary": "인증 구성을 위한 완벽한 가이드",
      "score": 0.95,
      "highlights": [
        "...애플리케이션에서 <em>인증을 구성</em>하는 단계..."
      ],
      "category": {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "name": "보안",
        "slug": "security"
      },
      "tags": ["authentication", "security", "configuration"]
    }
  ],
  "facets": {
    "categories": [
      {"id": "770e8400-e29b-41d4-a716-446655440002", "name": "보안", "count": 8},
      {"id": "880e8400-e29b-41d4-a716-446655440003", "name": "API", "count": 4}
    ],
    "tags": [
      {"name": "authentication", "count": 10},
      {"name": "configuration", "count": 7}
    ]
  }
}
```

#### GET /search/suggest
부분 쿼리를 기반으로 검색 제안 가져오기

**인증:** 선택사항

**쿼리 매개변수:**
- `q` (string, 필수): 부분 검색 쿼리 (최소 2자)
- `language` (string): 언어: en, ko (기본값: en)
- `limit` (integer): 최대 제안 수 (1-20, 기본값: 5)

**응답:**
```json
{
  "query": "인증",
  "suggestions": [
    "인증",
    "인가",
    "인증 구성",
    "인증 토큰",
    "인증 플로우"
  ]
}
```

#### POST /search/similar
의미적 유사성을 사용하여 유사한 콘텐츠 찾기

**요청 본문:**
```json
{
  "text": "사용자 인증과 JWT 토큰에 대한 도움이 필요합니다"
}
```

**쿼리 매개변수:**
- `language` (string): 언어: en, ko (기본값: en)
- `limit` (integer): 최대 결과 수 (1-50, 기본값: 10)

**응답:**
```json
{
  "text": "사용자 인증과 JWT 토큰에 대한 도움이 필요합니다",
  "language": "ko",
  "similar_items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "similarity": 0.92
    },
    {
      "id": "660e8400-e29b-41d4-a716-446655440001",
      "similarity": 0.87
    }
  ]
}
```

### 분석

#### GET /analytics/overview
조직의 분석 개요 가져오기

**인증:** 필수

**쿼리 매개변수:**
- `start_date` (datetime): 시작 날짜 (기본값: 30일 전)
- `end_date` (datetime): 종료 날짜 (기본값: 현재)

**응답:**
```json
{
  "total_items": 245,
  "published_items": 198,
  "total_views": 15420,
  "total_searches": 3876,
  "period": {
    "start_date": "2023-12-15T00:00:00Z",
    "end_date": "2024-01-15T00:00:00Z"
  }
}
```

#### GET /analytics/popular
조회수와 피드백을 기반으로 인기 콘텐츠 가져오기

**인증:** 필수

**쿼리 매개변수:**
- `period` (string): 기간: day, week, month, year (기본값: week)
- `limit` (integer): 최대 결과 수 (1-50, 기본값: 10)

**응답:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "title_ko": "시작 가이드",
    "title_en": "Getting Started Guide",
    "type": "article",
    "view_count": 1250,
    "helpful_count": 89,
    "helpful_percentage": 94.7
  }
]
```

#### GET /analytics/search-queries
검색 쿼리 분석 가져오기

**인증:** 필수

**쿼리 매개변수:**
- `period` (string): 기간: day, week, month (기본값: week)
- `limit` (integer): 최대 결과 수 (1-100, 기본값: 20)

**응답:**
```json
[
  {
    "query": "인증",
    "count": 145,
    "avg_results": 12.5
  },
  {
    "query": "구성",
    "count": 98,
    "avg_results": 8.3
  }
]
```

### 관리자

#### GET /admin/users
조직의 모든 사용자 목록 조회

**인증:** 필수 (관리자 역할)

**쿼리 매개변수:**
- `page` (integer): 페이지 번호 (기본값: 1)
- `limit` (integer): 페이지당 사용자 수 (기본값: 20)

**응답:**
```json
[
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "user@example.com",
    "username": "johndoe",
    "full_name": "John Doe",
    "role": "editor",
    "is_active": true,
    "is_verified": true,
    "last_login_at": "2024-01-15T10:30:00Z",
    "created_at": "2024-01-01T00:00:00Z"
  }
]
```

#### POST /admin/users
새 사용자 생성

**인증:** 필수 (관리자 역할)

**요청 본문:**
```json
{
  "email": "newuser@example.com",
  "username": "newuser",
  "password": "SecurePassword123!",
  "full_name": "New User",
  "role": "viewer"
}
```

**응답:** 201 Created
```json
{
  "id": "cc0e8400-e29b-41d4-a716-446655440007",
  "email": "newuser@example.com",
  "username": "newuser",
  "role": "viewer"
}
```

#### POST /admin/bulk-import
파일에서 지식 항목 대량 가져오기

**인증:** 필수 (관리자 역할)

**폼 데이터:**
- `file`: 업로드 파일 (CSV, JSON 또는 Markdown)
- `format`: 파일 형식 (csv, json, markdown)

**응답:** 202 Accepted
```json
{
  "job_id": "12345678-1234-5678-1234-567812345678",
  "status": "pending",
  "message": "data.csv에 대한 가져오기 작업이 생성되었습니다"
}
```

#### POST /admin/reindex
검색 인덱스 재구축 트리거

**인증:** 필수 (관리자 역할)

**쿼리 매개변수:**
- `force` (boolean): 완전한 재인덱싱 강제 (기본값: false)

**응답:** 202 Accepted
```json
{
  "status": "started",
  "message": "재인덱싱 작업이 대기열에 추가되었습니다",
  "force": false
}
```

## WebSocket 엔드포인트

API는 실시간 기능을 위한 WebSocket 연결을 지원합니다 (구현된 경우):

### WS /ws/notifications
인증된 사용자를 위한 실시간 알림

**연결 URL:**
```
ws://localhost:8000/ws/notifications?token=<access_token>
```

**메시지 형식:**
```json
{
  "type": "notification",
  "data": {
    "id": "notification-id",
    "message": "새 지식 항목이 게시되었습니다",
    "timestamp": "2024-01-15T12:00:00Z"
  }
}
```

## 보안 고려사항

1. **HTTPS 전용**: 모든 프로덕션 API 호출은 HTTPS를 사용해야 합니다
2. **토큰 보안**: URL이나 로그에 토큰을 노출하지 마세요
3. **CORS**: 프로덕션에서 특정 출처에 대해 구성됨
4. **입력 검증**: 모든 입력이 검증되고 살균됩니다
5. **SQL 인젝션**: ORM 및 매개변수화된 쿼리를 통해 보호됨
6. **XSS 보호**: 저장 전에 콘텐츠가 살균됩니다
7. **속도 제한**: 남용 및 DDoS 공격 방지
8. **감사 로깅**: 모든 민감한 작업이 기록됩니다

## API 버전 관리

API는 URL 경로 버전 관리를 사용합니다:
- 현재 버전: `/api/v1`
- 헤더의 버전: `API-Version: 1.0.0`

### 지원 중단 정책
- 지원 중단된 기능은 `Deprecation` 헤더로 표시됩니다
- 제거 전 최소 6개월 통지
- 호환성을 깨는 변경사항에 대한 마이그레이션 가이드 제공

## SDK 및 클라이언트 라이브러리

공식 SDK 사용 가능:
- Python: `pip install knowledge-db-client`
- JavaScript/TypeScript: `npm install @knowledge-db/client`
- Go: `go get github.com/knowledge-db/go-client`

## 지원 및 리소스

- **API 상태**: https://status.knowledge.example.com
- **개발자 포털**: https://developers.knowledge.example.com
- **지원 이메일**: api-support@knowledge.example.com
- **GitHub**: https://github.com/knowledge-db/api