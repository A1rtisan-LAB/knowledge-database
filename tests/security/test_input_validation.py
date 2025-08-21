"""Tests for input validation and sanitization."""

import pytest
from app.core.security_utils import (
    sanitize_input,
    validate_sql_input,
    validate_xss_input,
    validate_uuid,
    validate_email,
    validate_slug,
    safe_like_pattern,
    safe_query_parameters,
    SecureQueryBuilder
)


class TestInputSanitization:
    """Test input sanitization functions."""
    
    def test_sanitize_basic_input(self):
        """Test basic input sanitization."""
        result = sanitize_input("Normal input text")
        assert result == "Normal input text"
    
    def test_sanitize_html_tags(self):
        """Test HTML tag removal."""
        result = sanitize_input("<script>alert('xss')</script>")
        assert result == "alert('xss')"
        
        result = sanitize_input("<b>Bold</b> text")
        assert result == "Bold text"
    
    def test_sanitize_null_bytes(self):
        """Test null byte removal."""
        result = sanitize_input("text\x00with\x00null")
        assert result == "textwithnull"
    
    def test_sanitize_max_length(self):
        """Test max length enforcement."""
        long_text = "a" * 2000
        result = sanitize_input(long_text, max_length=100)
        assert len(result) == 100
    
    def test_sanitize_empty_input(self):
        """Test empty input handling."""
        assert sanitize_input("") == ""
        assert sanitize_input(None) == ""


class TestSQLInjectionValidation:
    """Test SQL injection detection."""
    
    def test_clean_input(self):
        """Test that clean input passes validation."""
        assert validate_sql_input("normal search term") is True
        assert validate_sql_input("user@example.com") is True
        assert validate_sql_input("product-123") is True
    
    def test_sql_keywords_detection(self):
        """Test detection of SQL keywords."""
        assert validate_sql_input("SELECT * FROM users") is False
        assert validate_sql_input("'; DROP TABLE users--") is False
        assert validate_sql_input("1 UNION SELECT password") is False
        assert validate_sql_input("'; DELETE FROM data--") is False
    
    def test_sql_comment_detection(self):
        """Test detection of SQL comments."""
        assert validate_sql_input("input -- comment") is False
        assert validate_sql_input("input /* comment */") is False
        assert validate_sql_input("input # comment") is False
    
    def test_sql_logic_detection(self):
        """Test detection of SQL logic attacks."""
        assert validate_sql_input("1 OR 1=1") is False
        assert validate_sql_input("' OR '1'='1") is False
        assert validate_sql_input("admin' AND 1=1") is False
    
    def test_sql_function_detection(self):
        """Test detection of dangerous SQL functions."""
        assert validate_sql_input("SLEEP(10)") is False
        assert validate_sql_input("BENCHMARK(1000000, SHA1('test'))") is False
        assert validate_sql_input("WAITFOR DELAY '00:00:10'") is False


class TestXSSValidation:
    """Test XSS detection."""
    
    def test_clean_input(self):
        """Test that clean input passes validation."""
        assert validate_xss_input("normal text") is True
        assert validate_xss_input("Hello, World!") is True
        assert validate_xss_input("user@example.com") is True
    
    def test_script_tag_detection(self):
        """Test detection of script tags."""
        assert validate_xss_input("<script>alert('xss')</script>") is False
        assert validate_xss_input("<SCRIPT>alert('xss')</SCRIPT>") is False
        assert validate_xss_input("<script src='evil.js'></script>") is False
    
    def test_javascript_protocol_detection(self):
        """Test detection of javascript: protocol."""
        assert validate_xss_input("javascript:alert('xss')") is False
        assert validate_xss_input("JAVASCRIPT:void(0)") is False
    
    def test_event_handler_detection(self):
        """Test detection of event handlers."""
        assert validate_xss_input("onclick='alert()'") is False
        assert validate_xss_input("onmouseover=alert(1)") is False
        assert validate_xss_input("onerror='hack()'") is False
    
    def test_iframe_detection(self):
        """Test detection of iframes."""
        assert validate_xss_input("<iframe src='evil.com'></iframe>") is False
        assert validate_xss_input("<IFRAME>") is False
    
    def test_embed_object_detection(self):
        """Test detection of embed and object tags."""
        assert validate_xss_input("<embed src='evil.swf'>") is False
        assert validate_xss_input("<object data='evil.swf'>") is False


class TestFormatValidation:
    """Test format validation functions."""
    
    def test_uuid_validation(self):
        """Test UUID format validation."""
        assert validate_uuid("123e4567-e89b-12d3-a456-426614174000") is True
        assert validate_uuid("123E4567-E89B-12D3-A456-426614174000") is True
        assert validate_uuid("not-a-uuid") is False
        assert validate_uuid("123e4567-e89b-12d3-a456") is False
        assert validate_uuid("123e4567e89b12d3a456426614174000") is False
    
    def test_email_validation(self):
        """Test email format validation."""
        assert validate_email("user@example.com") is True
        assert validate_email("test.user+tag@example.co.uk") is True
        assert validate_email("invalid.email") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
    
    def test_slug_validation(self):
        """Test slug format validation."""
        assert validate_slug("valid-slug") is True
        assert validate_slug("another-valid-slug-123") is True
        assert validate_slug("simpletext") is True
        assert validate_slug("Invalid Slug") is False
        assert validate_slug("invalid_slug") is False
        assert validate_slug("invalid.slug") is False


class TestSafeLikePattern:
    """Test LIKE pattern escaping."""
    
    def test_escape_percent(self):
        """Test escaping of percent sign."""
        assert safe_like_pattern("100%") == "100\\%"
        assert safe_like_pattern("%wildcard%") == "\\%wildcard\\%"
    
    def test_escape_underscore(self):
        """Test escaping of underscore."""
        assert safe_like_pattern("user_name") == "user\\_name"
        assert safe_like_pattern("_private") == "\\_private"
    
    def test_escape_backslash(self):
        """Test escaping of backslash."""
        assert safe_like_pattern("path\\to\\file") == "path\\\\to\\\\file"
    
    def test_escape_brackets(self):
        """Test escaping of brackets."""
        assert safe_like_pattern("[admin]") == "\\[admin]"
    
    def test_combined_escaping(self):
        """Test combined character escaping."""
        assert safe_like_pattern("50%_off_[sale]") == "50\\%\\_off\\_\\[sale]"


class TestSafeQueryParameters:
    """Test query parameter sanitization."""
    
    def test_string_sanitization(self):
        """Test string parameter sanitization."""
        params = {
            "name": "<script>alert('xss')</script>",
            "email": "user@example.com"
        }
        result = safe_query_parameters(params)
        assert result["name"] == "alert('xss')"
        assert result["email"] == "user@example.com"
    
    def test_list_sanitization(self):
        """Test list parameter sanitization."""
        params = {
            "tags": ["<b>tag1</b>", "tag2", "<script>tag3</script>"]
        }
        result = safe_query_parameters(params)
        assert result["tags"] == ["tag1", "tag2", "tag3"]
    
    def test_mixed_type_parameters(self):
        """Test mixed type parameter handling."""
        params = {
            "name": "test",
            "age": 25,
            "active": True,
            "score": 99.5,
            "data": None
        }
        result = safe_query_parameters(params)
        assert result["name"] == "test"
        assert result["age"] == 25
        assert result["active"] is True
        assert result["score"] == 99.5
        assert result["data"] is None


class TestSecureQueryBuilder:
    """Test secure query builder."""
    
    def test_validate_column_name(self):
        """Test column name validation."""
        allowed = ["id", "name", "email", "created_at"]
        
        assert SecureQueryBuilder.validate_column_name("name", allowed) is True
        assert SecureQueryBuilder.validate_column_name("email", allowed) is True
        assert SecureQueryBuilder.validate_column_name("password", allowed) is False
        assert SecureQueryBuilder.validate_column_name("'; DROP TABLE--", allowed) is False
    
    def test_validate_table_name(self):
        """Test table name validation."""
        allowed = ["users", "products", "orders"]
        
        assert SecureQueryBuilder.validate_table_name("users", allowed) is True
        assert SecureQueryBuilder.validate_table_name("products", allowed) is True
        assert SecureQueryBuilder.validate_table_name("admin", allowed) is False
        assert SecureQueryBuilder.validate_table_name("users; DELETE", allowed) is False