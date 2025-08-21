# Knowledge Database API Documentation

## Table of Contents
- [Overview](#overview)
- [Base URL](#base-url)
- [Authentication](#authentication)
- [Rate Limiting](#rate-limiting)
- [Error Handling](#error-handling)
- [Pagination](#pagination)
- [API Endpoints](#api-endpoints)
  - [Root Endpoints](#root-endpoints)
  - [Authentication](#authentication-endpoints)
  - [Knowledge Items](#knowledge-items)
  - [Categories](#categories)
  - [Search](#search)
  - [Analytics](#analytics)
  - [Admin](#admin)

## Overview

The Knowledge Database API is a comprehensive RESTful API for managing organizational knowledge with AI-powered search capabilities and bilingual (English/Korean) support. Built with FastAPI, it provides automatic OpenAPI documentation, robust authentication, and enterprise-grade security features.

### Key Features
- JWT-based authentication with refresh tokens
- Role-based access control (RBAC)
- Multi-language support (English and Korean)
- AI-powered semantic search using OpenSearch
- Real-time analytics and metrics
- Rate limiting and request throttling
- Comprehensive audit logging

## Base URL

```
Production: https://api.knowledge.example.com/api/v1
Development: http://localhost:8000/api/v1
```

## Authentication

The API uses JWT (JSON Web Token) bearer authentication. Most endpoints require authentication.

### Authentication Flow

1. **Login**: POST to `/auth/login` with credentials to receive access and refresh tokens
2. **Use Access Token**: Include in Authorization header: `Authorization: Bearer <access_token>`
3. **Refresh Token**: When access token expires, use refresh token to get new tokens
4. **Logout**: POST to `/auth/logout` to invalidate session

### Token Expiration
- Access Token: 30 minutes
- Refresh Token: 7 days

### User Roles
- `viewer`: Read-only access to published content
- `editor`: Can create, edit, and publish content
- `admin`: Full system access including user management

### Authorization Header

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Rate Limiting

API implements rate limiting to prevent abuse:

- **Default Limits**: 100 requests per 60 seconds per user
- **Burst Limits**: Maximum 10 requests per second
- **Headers Returned**:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Requests remaining in current window
  - `X-RateLimit-Reset`: Unix timestamp when limit resets

### Rate Limit Response

```json
{
  "error": "rate_limit_exceeded",
  "message": "Rate limit exceeded. Please try again later.",
  "retry_after": 45
}
```

## Error Handling

The API returns consistent error responses with appropriate HTTP status codes.

### Error Response Format

```json
{
  "error": "error_code",
  "message": "Human-readable error message",
  "details": {
    "field": "Additional context about the error"
  }
}
```

### Common HTTP Status Codes

| Status Code | Description |
|------------|-------------|
| 200 | OK - Request successful |
| 201 | Created - Resource created successfully |
| 204 | No Content - Request successful, no content returned |
| 400 | Bad Request - Invalid request parameters |
| 401 | Unauthorized - Authentication required or invalid |
| 403 | Forbidden - Insufficient permissions |
| 404 | Not Found - Resource not found |
| 409 | Conflict - Resource already exists |
| 422 | Unprocessable Entity - Validation error |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |

## Pagination

List endpoints support pagination using query parameters:

### Pagination Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (1-indexed) |
| `limit` | integer | 20 | Items per page (max 100) |

### Paginated Response Format

```json
{
  "items": [...],
  "total": 150,
  "page": 1,
  "limit": 20,
  "has_more": true
}
```

## API Endpoints

### Root Endpoints

#### GET /
Get API information

**Response:**
```json
{
  "name": "Knowledge Database API",
  "version": "1.0.0",
  "status": "healthy",
  "docs": "/docs"
}
```

#### GET /health
Health check endpoint for monitoring

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "environment": "production"
}
```

### Authentication Endpoints

#### POST /auth/login
Authenticate user and receive tokens

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "securePassword123",
  "organization_slug": "optional-org-slug"
}
```

**Response:**
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
Refresh access token using refresh token

**Request Body:**
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer"
}
```

#### POST /auth/logout
Logout current user

**Authorization:** Required

**Response:** 204 No Content

#### GET /auth/me
Get current user information

**Authorization:** Required

**Response:**
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

### Knowledge Items

#### GET /knowledge
List knowledge items with filtering and pagination

**Authorization:** Optional (shows only published items for non-authenticated users)

**Query Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `page` | integer | No | Page number (default: 1) |
| `limit` | integer | No | Items per page (1-100, default: 20) |
| `category_id` | uuid | No | Filter by category ID |
| `type` | string | No | Filter by content type |
| `status` | string | No | Filter by status (editors only) |
| `tags` | array[string] | No | Filter by tags (must have all) |
| `language` | string | No | Language preference: en, ko (default: en) |
| `sort` | string | No | Sort by: created_at, updated_at, title, views, helpful |
| `order` | string | No | Sort order: asc, desc (default: desc) |

**Response:**
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
Get detailed knowledge item by ID

**Authorization:** Optional (required for non-published items)

**Path Parameters:**
- `id` (uuid): Knowledge item ID

**Query Parameters:**
- `language` (string): Language preference: en, ko (default: en)
- `include_related` (boolean): Include related items (default: false)

**Response:**
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
Create a new knowledge item

**Authorization:** Required (editor role)

**Request Body:**
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

**Response:** 201 Created
```json
{
  "id": "880e8400-e29b-41d4-a716-446655440003",
  "type": "article",
  "slug": "new-feature-guide",
  ...
}
```

#### PUT /knowledge/{id}
Update a knowledge item

**Authorization:** Required (editor role)

**Path Parameters:**
- `id` (uuid): Knowledge item ID

**Request Body:** (all fields optional)
```json
{
  "title_ko": "업데이트된 제목",
  "title_en": "Updated Title",
  "content_ko": "업데이트된 내용",
  "content_en": "Updated content",
  "tags": ["updated", "feature"]
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "type": "article",
  ...
}
```

#### DELETE /knowledge/{id}
Soft delete a knowledge item

**Authorization:** Required (editor role)

**Path Parameters:**
- `id` (uuid): Knowledge item ID

**Response:** 204 No Content

#### POST /knowledge/{id}/publish
Publish a knowledge item

**Authorization:** Required (editor role)

**Path Parameters:**
- `id` (uuid): Knowledge item ID

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "published",
  "published_at": "2024-01-15T12:00:00Z",
  ...
}
```

#### GET /knowledge/{id}/versions
Get version history for a knowledge item

**Authorization:** Required

**Path Parameters:**
- `id` (uuid): Knowledge item ID

**Response:**
```json
[
  {
    "id": "990e8400-e29b-41d4-a716-446655440004",
    "version_number": 2,
    "title_ko": "업데이트된 가이드",
    "title_en": "Updated Guide",
    "change_summary": "Added new section about advanced features",
    "created_at": "2024-01-12T10:00:00Z"
  },
  {
    "id": "aa0e8400-e29b-41d4-a716-446655440005",
    "version_number": 1,
    "title_ko": "원본 가이드",
    "title_en": "Original Guide",
    "change_summary": "Initial version",
    "created_at": "2024-01-09T10:00:00Z"
  }
]
```

### Categories

#### GET /categories
List categories with hierarchy

**Authorization:** Required

**Query Parameters:**
- `parent_id` (uuid): Filter by parent category (null for root categories)
- `language` (string): Language preference: en, ko (default: en)

**Response:**
```json
[
  {
    "id": "770e8400-e29b-41d4-a716-446655440002",
    "parent_id": null,
    "name": "Getting Started",
    "slug": "getting-started",
    "description": "Beginner guides and tutorials",
    "icon": "book",
    "display_order": 1,
    "item_count": 15
  },
  {
    "id": "880e8400-e29b-41d4-a716-446655440003",
    "parent_id": null,
    "name": "Advanced Topics",
    "slug": "advanced",
    "description": "Advanced features and concepts",
    "icon": "graduation-cap",
    "display_order": 2,
    "item_count": 23
  }
]
```

#### GET /categories/{id}
Get category details with children

**Authorization:** Required

**Path Parameters:**
- `id` (uuid): Category ID

**Query Parameters:**
- `language` (string): Language preference: en, ko (default: en)

**Response:**
```json
{
  "id": "770e8400-e29b-41d4-a716-446655440002",
  "parent_id": null,
  "name": "Getting Started",
  "slug": "getting-started",
  "description": "Beginner guides and tutorials",
  "icon": "book",
  "display_order": 1,
  "item_count": 15,
  "children": [
    {
      "id": "990e8400-e29b-41d4-a716-446655440004",
      "name": "Installation",
      "slug": "installation",
      "item_count": 5
    },
    {
      "id": "aa0e8400-e29b-41d4-a716-446655440005",
      "name": "Configuration",
      "slug": "configuration",
      "item_count": 10
    }
  ]
}
```

#### POST /categories
Create a new category

**Authorization:** Required (editor role)

**Request Body:**
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

**Response:** 201 Created
```json
{
  "id": "bb0e8400-e29b-41d4-a716-446655440006",
  "name_ko": "새 카테고리",
  "name_en": "New Category",
  "slug": "new-category",
  "parent_id": null
}
```

### Search

#### POST /search
Search knowledge base with AI-powered semantic search

**Authorization:** Optional

**Request Body:**
```json
{
  "query": "how to configure authentication"
}
```

**Query Parameters:**
- `language` (string): Language: en, ko (default: en)
- `search_type` (string): Type: keyword, semantic, hybrid (default: hybrid)
- `page` (integer): Page number (default: 1)
- `limit` (integer): Results per page (1-100, default: 20)
- `category_ids` (array[string]): Filter by category IDs
- `types` (array[string]): Filter by content types
- `tags` (array[string]): Filter by tags

**Response:**
```json
{
  "query": "how to configure authentication",
  "total": 12,
  "page": 1,
  "limit": 20,
  "results": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "title": "Authentication Configuration Guide",
      "slug": "auth-configuration",
      "summary": "Complete guide to configuring authentication",
      "score": 0.95,
      "highlights": [
        "...steps to <em>configure authentication</em> in your application..."
      ],
      "category": {
        "id": "770e8400-e29b-41d4-a716-446655440002",
        "name": "Security",
        "slug": "security"
      },
      "tags": ["authentication", "security", "configuration"]
    }
  ],
  "facets": {
    "categories": [
      {"id": "770e8400-e29b-41d4-a716-446655440002", "name": "Security", "count": 8},
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
Get search suggestions based on partial query

**Authorization:** Optional

**Query Parameters:**
- `q` (string, required): Partial search query (min 2 characters)
- `language` (string): Language: en, ko (default: en)
- `limit` (integer): Max suggestions (1-20, default: 5)

**Response:**
```json
{
  "query": "auth",
  "suggestions": [
    "authentication",
    "authorization",
    "auth configuration",
    "auth token",
    "auth flow"
  ]
}
```

#### POST /search/similar
Find similar content using semantic similarity

**Request Body:**
```json
{
  "text": "I need help with user authentication and JWT tokens"
}
```

**Query Parameters:**
- `language` (string): Language: en, ko (default: en)
- `limit` (integer): Max results (1-50, default: 10)

**Response:**
```json
{
  "text": "I need help with user authentication and JWT tokens",
  "language": "en",
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

### Analytics

#### GET /analytics/overview
Get analytics overview for the organization

**Authorization:** Required

**Query Parameters:**
- `start_date` (datetime): Start date (default: 30 days ago)
- `end_date` (datetime): End date (default: now)

**Response:**
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
Get popular content based on views and feedback

**Authorization:** Required

**Query Parameters:**
- `period` (string): Time period: day, week, month, year (default: week)
- `limit` (integer): Max results (1-50, default: 10)

**Response:**
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
Get search query analytics

**Authorization:** Required

**Query Parameters:**
- `period` (string): Time period: day, week, month (default: week)
- `limit` (integer): Max results (1-100, default: 20)

**Response:**
```json
[
  {
    "query": "authentication",
    "count": 145,
    "avg_results": 12.5
  },
  {
    "query": "configuration",
    "count": 98,
    "avg_results": 8.3
  }
]
```

### Admin

#### GET /admin/users
List all users in the organization

**Authorization:** Required (admin role)

**Query Parameters:**
- `page` (integer): Page number (default: 1)
- `limit` (integer): Users per page (default: 20)

**Response:**
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
Create a new user

**Authorization:** Required (admin role)

**Request Body:**
```json
{
  "email": "newuser@example.com",
  "username": "newuser",
  "password": "SecurePassword123!",
  "full_name": "New User",
  "role": "viewer"
}
```

**Response:** 201 Created
```json
{
  "id": "cc0e8400-e29b-41d4-a716-446655440007",
  "email": "newuser@example.com",
  "username": "newuser",
  "role": "viewer"
}
```

#### POST /admin/bulk-import
Bulk import knowledge items from file

**Authorization:** Required (admin role)

**Form Data:**
- `file`: Upload file (CSV, JSON, or Markdown)
- `format`: File format (csv, json, markdown)

**Response:** 202 Accepted
```json
{
  "job_id": "12345678-1234-5678-1234-567812345678",
  "status": "pending",
  "message": "Import job created for data.csv"
}
```

#### POST /admin/reindex
Trigger search index rebuild

**Authorization:** Required (admin role)

**Query Parameters:**
- `force` (boolean): Force complete reindex (default: false)

**Response:** 202 Accepted
```json
{
  "status": "started",
  "message": "Reindexing job has been queued",
  "force": false
}
```

## WebSocket Endpoints

The API supports WebSocket connections for real-time features (if implemented):

### WS /ws/notifications
Real-time notifications for authenticated users

**Connection URL:**
```
ws://localhost:8000/ws/notifications?token=<access_token>
```

**Message Format:**
```json
{
  "type": "notification",
  "data": {
    "id": "notification-id",
    "message": "New knowledge item published",
    "timestamp": "2024-01-15T12:00:00Z"
  }
}
```

## Security Considerations

1. **HTTPS Only**: All production API calls must use HTTPS
2. **Token Security**: Never expose tokens in URLs or logs
3. **CORS**: Configured for specific origins in production
4. **Input Validation**: All inputs are validated and sanitized
5. **SQL Injection**: Protected through ORM and parameterized queries
6. **XSS Protection**: Content is sanitized before storage
7. **Rate Limiting**: Prevents abuse and DDoS attacks
8. **Audit Logging**: All sensitive operations are logged

## API Versioning

The API uses URL path versioning:
- Current version: `/api/v1`
- Version in headers: `API-Version: 1.0.0`

### Deprecation Policy
- Deprecated features marked with `Deprecation` header
- Minimum 6 months notice before removal
- Migration guides provided for breaking changes

## SDK and Client Libraries

Official SDKs available for:
- Python: `pip install knowledge-db-client`
- JavaScript/TypeScript: `npm install @knowledge-db/client`
- Go: `go get github.com/knowledge-db/go-client`

## Support and Resources

- **API Status**: https://status.knowledge.example.com
- **Developer Portal**: https://developers.knowledge.example.com
- **Support Email**: api-support@knowledge.example.com
- **GitHub**: https://github.com/knowledge-db/api