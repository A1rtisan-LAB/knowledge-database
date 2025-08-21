#!/usr/bin/env python3
"""
Generate OpenAPI specification from FastAPI application.

This script extracts the OpenAPI schema from the FastAPI app and saves it
to a YAML file for documentation and client generation purposes.
"""

import json
import yaml
import sys
import os
from pathlib import Path

# Add parent directory to path to import app
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app
from app.core.config import get_settings

def generate_openapi_spec():
    """Generate OpenAPI specification from FastAPI app."""
    settings = get_settings()
    
    # Get the OpenAPI schema from FastAPI
    openapi_schema = app.openapi()
    
    # Enhanced OpenAPI schema with additional information
    openapi_schema["info"]["description"] = """
    # Knowledge Database API
    
    Comprehensive knowledge management system with AI-powered search and bilingual support.
    
    ## Features
    - JWT-based authentication with refresh tokens
    - Role-based access control (viewer, editor, admin)
    - Multi-language support (English and Korean)
    - AI-powered semantic search using OpenSearch
    - Real-time analytics and metrics
    - Rate limiting and request throttling
    - Comprehensive audit logging
    
    ## Authentication
    Most endpoints require authentication using JWT bearer tokens.
    Include the token in the Authorization header: `Bearer <token>`
    
    ## Rate Limiting
    - Default: 100 requests per 60 seconds per user
    - Burst: Maximum 10 requests per second
    
    ## Language Support
    Use the `language` query parameter to specify language preference:
    - `en` for English (default)
    - `ko` for Korean
    """
    
    # Add servers
    openapi_schema["servers"] = [
        {
            "url": "https://api.knowledge.example.com/api/v1",
            "description": "Production server"
        },
        {
            "url": "http://localhost:8000/api/v1",
            "description": "Development server"
        }
    ]
    
    # Add security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "JWT authentication token"
        }
    }
    
    # Add global security requirement
    openapi_schema["security"] = [{"bearerAuth": []}]
    
    # Add tags with descriptions
    openapi_schema["tags"] = [
        {
            "name": "Authentication",
            "description": "User authentication and token management"
        },
        {
            "name": "Knowledge Items",
            "description": "Create, read, update, and delete knowledge items"
        },
        {
            "name": "Categories",
            "description": "Manage knowledge categories and hierarchy"
        },
        {
            "name": "Search",
            "description": "AI-powered search with semantic and keyword matching"
        },
        {
            "name": "Analytics",
            "description": "Usage analytics and insights"
        },
        {
            "name": "Admin",
            "description": "Administrative functions for system management"
        }
    ]
    
    # Add example responses
    openapi_schema["components"]["responses"] = {
        "UnauthorizedError": {
            "description": "Authentication information is missing or invalid",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string", "example": "unauthorized"},
                            "message": {"type": "string", "example": "Invalid or expired token"}
                        }
                    }
                }
            }
        },
        "ForbiddenError": {
            "description": "User does not have permission to access this resource",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string", "example": "forbidden"},
                            "message": {"type": "string", "example": "You don't have permission to access this resource"}
                        }
                    }
                }
            }
        },
        "NotFoundError": {
            "description": "The requested resource was not found",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string", "example": "not_found"},
                            "message": {"type": "string", "example": "Resource not found"}
                        }
                    }
                }
            }
        },
        "ValidationError": {
            "description": "Request validation failed",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string", "example": "validation_error"},
                            "message": {"type": "string", "example": "Validation failed"},
                            "details": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "loc": {"type": "array", "items": {"type": "string"}},
                                        "msg": {"type": "string"},
                                        "type": {"type": "string"}
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        "RateLimitError": {
            "description": "Rate limit exceeded",
            "content": {
                "application/json": {
                    "schema": {
                        "type": "object",
                        "properties": {
                            "error": {"type": "string", "example": "rate_limit_exceeded"},
                            "message": {"type": "string", "example": "Rate limit exceeded. Please try again later."},
                            "retry_after": {"type": "integer", "example": 45}
                        }
                    }
                }
            }
        }
    }
    
    # Add external documentation
    openapi_schema["externalDocs"] = {
        "description": "Full API Documentation",
        "url": "https://developers.knowledge.example.com/api"
    }
    
    # Save as YAML
    output_dir = Path(__file__).parent.parent / "docs" / "api"
    output_dir.mkdir(parents=True, exist_ok=True)
    
    yaml_file = output_dir / "openapi.yaml"
    with open(yaml_file, "w", encoding="utf-8") as f:
        yaml.dump(openapi_schema, f, sort_keys=False, allow_unicode=True, default_flow_style=False)
    
    print(f"✓ OpenAPI specification generated: {yaml_file}")
    
    # Also save as JSON for compatibility
    json_file = output_dir / "openapi.json"
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    
    print(f"✓ OpenAPI specification generated: {json_file}")
    
    # Print summary
    print("\nAPI Summary:")
    print(f"  Title: {openapi_schema['info']['title']}")
    print(f"  Version: {openapi_schema['info']['version']}")
    print(f"  Total Paths: {len(openapi_schema['paths'])}")
    
    # Count operations
    operations = 0
    for path, methods in openapi_schema['paths'].items():
        operations += len([m for m in methods if m in ['get', 'post', 'put', 'delete', 'patch']])
    print(f"  Total Operations: {operations}")
    
    # List all endpoints
    print("\nEndpoints:")
    for path in sorted(openapi_schema['paths'].keys()):
        methods = openapi_schema['paths'][path]
        for method in ['get', 'post', 'put', 'delete', 'patch']:
            if method in methods:
                operation_id = methods[method].get('operationId', 'N/A')
                summary = methods[method].get('summary', 'N/A')
                print(f"  {method.upper():6} {path:40} {summary}")

if __name__ == "__main__":
    try:
        generate_openapi_spec()
    except Exception as e:
        print(f"Error generating OpenAPI specification: {e}", file=sys.stderr)
        sys.exit(1)