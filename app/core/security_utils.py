"""Security utilities for the application."""

import re
import bleach
from typing import Any, List, Optional
from sqlalchemy import text
from sqlalchemy.sql import Select
import structlog

logger = structlog.get_logger()

# SQL injection patterns to detect
SQL_INJECTION_PATTERNS = [
    r"(\b(SELECT|INSERT|UPDATE|DELETE|DROP|UNION|ALTER|CREATE|EXEC|EXECUTE)\b)",
    r"(--|#|\/\*|\*\/)",
    r"(\bOR\b\s+\d+\s*=\s*\d+)",
    r"(\bAND\b\s+\d+\s*=\s*\d+)",
    r"(\'|\"|;|\\x00|\\n|\\r|\\x1a)",
    r"(\bSLEEP\b|\bBENCHMARK\b|\bWAITFOR\b)",
]

# XSS patterns to detect
XSS_PATTERNS = [
    r"(<script[^>]*>.*?</script>)",
    r"(javascript:)",
    r"(on\w+\s*=)",
    r"(<iframe[^>]*>)",
    r"(<embed[^>]*>)",
    r"(<object[^>]*>)",
]


def sanitize_input(value: str, max_length: int = 1000) -> str:
    """
    Sanitize user input to prevent injection attacks.
    
    Args:
        value: Input value to sanitize
        max_length: Maximum allowed length
        
    Returns:
        str: Sanitized input
    """
    if not value:
        return ""
    
    # Truncate to max length
    value = value[:max_length]
    
    # Remove null bytes and control characters
    value = value.replace("\x00", "").replace("\r", "").replace("\n", " ")
    
    # Basic HTML sanitization
    value = bleach.clean(value, tags=[], strip=True)
    
    return value.strip()


def validate_sql_input(value: str) -> bool:
    """
    Validate input for potential SQL injection patterns.
    
    Args:
        value: Input value to validate
        
    Returns:
        bool: True if safe, False if potential injection detected
    """
    if not value:
        return True
    
    value_upper = value.upper()
    
    for pattern in SQL_INJECTION_PATTERNS:
        if re.search(pattern, value_upper, re.IGNORECASE):
            logger.warning(
                "Potential SQL injection detected",
                pattern=pattern,
                value=value[:100]  # Log only first 100 chars
            )
            return False
    
    return True


def validate_xss_input(value: str) -> bool:
    """
    Validate input for potential XSS patterns.
    
    Args:
        value: Input value to validate
        
    Returns:
        bool: True if safe, False if potential XSS detected
    """
    if not value:
        return True
    
    for pattern in XSS_PATTERNS:
        if re.search(pattern, value, re.IGNORECASE):
            logger.warning(
                "Potential XSS detected",
                pattern=pattern,
                value=value[:100]  # Log only first 100 chars
            )
            return False
    
    return True


def safe_like_pattern(value: str) -> str:
    """
    Escape special characters in LIKE patterns.
    
    Args:
        value: Value to escape
        
    Returns:
        str: Escaped value safe for LIKE queries
    """
    # Escape special LIKE characters
    value = value.replace("\\", "\\\\")
    value = value.replace("%", "\\%")
    value = value.replace("_", "\\_")
    value = value.replace("[", "\\[")
    return value


def validate_uuid(value: str) -> bool:
    """
    Validate UUID format.
    
    Args:
        value: Value to validate
        
    Returns:
        bool: True if valid UUID format
    """
    uuid_pattern = r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
    return bool(re.match(uuid_pattern, value.lower()))


def validate_email(email: str) -> bool:
    """
    Validate email format.
    
    Args:
        email: Email to validate
        
    Returns:
        bool: True if valid email format
    """
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(email_pattern, email))


def validate_slug(slug: str) -> bool:
    """
    Validate slug format (alphanumeric with hyphens).
    
    Args:
        slug: Slug to validate
        
    Returns:
        bool: True if valid slug format
    """
    slug_pattern = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
    return bool(re.match(slug_pattern, slug.lower()))


def safe_query_parameters(params: dict) -> dict:
    """
    Sanitize query parameters for database queries.
    
    Args:
        params: Dictionary of parameters
        
    Returns:
        dict: Sanitized parameters
    """
    safe_params = {}
    
    for key, value in params.items():
        if isinstance(value, str):
            # Sanitize string values
            safe_params[key] = sanitize_input(value)
        elif isinstance(value, (list, tuple)):
            # Sanitize list/tuple values
            safe_params[key] = [
                sanitize_input(v) if isinstance(v, str) else v
                for v in value
            ]
        else:
            # Keep other types as-is (int, float, bool, None)
            safe_params[key] = value
    
    return safe_params


class SecureQueryBuilder:
    """Helper class for building secure database queries."""
    
    @staticmethod
    def validate_column_name(column_name: str, allowed_columns: List[str]) -> bool:
        """
        Validate column name against whitelist.
        
        Args:
            column_name: Column name to validate
            allowed_columns: List of allowed column names
            
        Returns:
            bool: True if valid column name
        """
        return column_name in allowed_columns
    
    @staticmethod
    def validate_table_name(table_name: str, allowed_tables: List[str]) -> bool:
        """
        Validate table name against whitelist.
        
        Args:
            table_name: Table name to validate
            allowed_tables: List of allowed table names
            
        Returns:
            bool: True if valid table name
        """
        return table_name in allowed_tables
    
    @staticmethod
    def build_safe_order_by(query: Select, order_by: str, allowed_columns: List[str]) -> Select:
        """
        Build safe ORDER BY clause.
        
        Args:
            query: SQLAlchemy query
            order_by: Order by string (e.g., "created_at desc")
            allowed_columns: List of allowed column names
            
        Returns:
            Select: Query with safe ORDER BY
        """
        if not order_by:
            return query
        
        parts = order_by.lower().split()
        if not parts:
            return query
        
        column = parts[0]
        direction = parts[1] if len(parts) > 1 else "asc"
        
        # Validate column name
        if column not in allowed_columns:
            logger.warning(f"Invalid order_by column: {column}")
            return query
        
        # Validate direction
        if direction not in ["asc", "desc"]:
            logger.warning(f"Invalid order_by direction: {direction}")
            direction = "asc"
        
        # Apply order by using parameterized approach
        if direction == "desc":
            return query.order_by(text(f"{column} DESC"))
        else:
            return query.order_by(text(f"{column} ASC"))
    
    @staticmethod
    def build_safe_filter(query: Select, filters: dict, allowed_columns: List[str]) -> Select:
        """
        Build safe WHERE clause with filters.
        
        Args:
            query: SQLAlchemy query
            filters: Dictionary of filters
            allowed_columns: List of allowed column names
            
        Returns:
            Select: Query with safe filters
        """
        for column, value in filters.items():
            # Validate column name
            if column not in allowed_columns:
                logger.warning(f"Invalid filter column: {column}")
                continue
            
            # Skip None values
            if value is None:
                continue
            
            # Apply filter using parameterized query
            if isinstance(value, (list, tuple)):
                query = query.where(text(f"{column} IN :values").params(values=value))
            else:
                query = query.where(text(f"{column} = :value").params(value=value))
        
        return query