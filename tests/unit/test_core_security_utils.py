"""Comprehensive tests for security utilities."""

import pytest
from unittest.mock import patch, MagicMock
from sqlalchemy import text
from sqlalchemy.sql import Select

from app.core.security_utils import (
    sanitize_input,
    validate_sql_input,
    validate_xss_input,
    safe_like_pattern,
    validate_uuid,
    validate_email,
    validate_slug,
    safe_query_parameters,
    SecureQueryBuilder,
    SQL_INJECTION_PATTERNS,
    XSS_PATTERNS
)


class TestSanitizeInput:
    """Test cases for sanitize_input function."""
    
    def test_empty_input(self):
        """Test sanitization of empty input."""
        assert sanitize_input("") == ""
        assert sanitize_input(None) == ""
    
    def test_max_length_truncation(self):
        """Test input truncation to max length."""
        long_input = "a" * 2000
        result = sanitize_input(long_input, max_length=100)
        assert len(result) == 100
    
    def test_null_byte_removal(self):
        """Test removal of null bytes."""
        input_with_null = "test\x00data"
        result = sanitize_input(input_with_null)
        assert "\x00" not in result
        assert result == "test data"
    
    def test_control_character_replacement(self):
        """Test replacement of control characters."""
        input_with_control = "test\rdata\nmore"
        result = sanitize_input(input_with_control)
        assert "\r" not in result
        assert "\n" not in result
        assert result == "test data more"
    
    def test_html_sanitization(self):
        """Test HTML tag removal."""
        html_input = "<script>alert('xss')</script>Normal text"
        result = sanitize_input(html_input)
        assert "<script>" not in result
        assert "alert" in result  # Content preserved but tags removed
        assert "Normal text" in result
    
    def test_whitespace_trimming(self):
        """Test whitespace trimming."""
        input_with_spaces = "  test data  "
        result = sanitize_input(input_with_spaces)
        assert result == "test data"
    
    def test_combined_sanitization(self):
        """Test combined sanitization scenarios."""
        complex_input = "  <b>Test</b>\x00\r\nData  "
        result = sanitize_input(complex_input, max_length=50)
        assert len(result) <= 50
        assert "<b>" not in result
        assert "\x00" not in result
        assert "\r" not in result
        assert "\n" not in result
        assert result.strip() == result


class TestValidateSqlInput:
    """Test cases for validate_sql_input function."""
    
    def test_empty_input(self):
        """Test validation of empty input."""
        assert validate_sql_input("") is True
        assert validate_sql_input(None) is True
    
    def test_safe_input(self):
        """Test validation of safe input."""
        assert validate_sql_input("normal text") is True
        assert validate_sql_input("user@example.com") is True
        assert validate_sql_input("product-123") is True
    
    @pytest.mark.parametrize("sql_injection", [
        "'; DROP TABLE users; --",
        "1 OR 1=1",
        "admin' --",
        "1 UNION SELECT * FROM users",
        "'; DELETE FROM products; --",
        "1; INSERT INTO users VALUES('hacker', 'pass')",
        "1; UPDATE users SET admin=1",
        "'; ALTER TABLE users ADD COLUMN hack INT; --",
        "'; CREATE TABLE hack (id INT); --",
        "'; EXEC sp_executesql N'SELECT * FROM users'; --",
        "'; EXECUTE('SELECT * FROM passwords'); --",
        "SLEEP(5)--",
        "BENCHMARK(1000000,MD5('test'))",
        "'; WAITFOR DELAY '00:00:05'--"
    ])
    def test_sql_injection_detection(self, sql_injection):
        """Test detection of SQL injection patterns."""
        with patch('app.core.security_utils.logger') as mock_logger:
            assert validate_sql_input(sql_injection) is False
            mock_logger.warning.assert_called()
    
    def test_case_insensitive_detection(self):
        """Test case insensitive SQL injection detection."""
        with patch('app.core.security_utils.logger'):
            assert validate_sql_input("select * from users") is False
            assert validate_sql_input("SELECT * FROM users") is False
            assert validate_sql_input("SeLeCt * FrOm users") is False
    
    def test_comment_detection(self):
        """Test detection of SQL comments."""
        with patch('app.core.security_utils.logger'):
            assert validate_sql_input("data -- comment") is False
            assert validate_sql_input("data # comment") is False
            assert validate_sql_input("data /* comment */") is False
    
    def test_special_character_detection(self):
        """Test detection of special SQL characters."""
        with patch('app.core.security_utils.logger'):
            assert validate_sql_input("data; more") is False
            assert validate_sql_input("data' OR '1'='1") is False
            assert validate_sql_input('data" OR "1"="1') is False


class TestValidateXssInput:
    """Test cases for validate_xss_input function."""
    
    def test_empty_input(self):
        """Test validation of empty input."""
        assert validate_xss_input("") is True
        assert validate_xss_input(None) is True
    
    def test_safe_input(self):
        """Test validation of safe input."""
        assert validate_xss_input("normal text") is True
        assert validate_xss_input("user@example.com") is True
        assert validate_xss_input("product-123") is True
    
    @pytest.mark.parametrize("xss_payload", [
        "<script>alert('xss')</script>",
        "<script src='evil.js'></script>",
        "javascript:alert('xss')",
        "<img src=x onerror=alert('xss')>",
        "<body onload=alert('xss')>",
        "<iframe src='evil.com'></iframe>",
        "<embed src='evil.swf'>",
        "<object data='evil.swf'></object>",
        "<svg onload=alert('xss')>",
        "onclick=alert('xss')",
        "onmouseover=alert('xss')"
    ])
    def test_xss_detection(self, xss_payload):
        """Test detection of XSS patterns."""
        with patch('app.core.security_utils.logger') as mock_logger:
            assert validate_xss_input(xss_payload) is False
            mock_logger.warning.assert_called()
    
    def test_case_insensitive_detection(self):
        """Test case insensitive XSS detection."""
        with patch('app.core.security_utils.logger'):
            assert validate_xss_input("<SCRIPT>alert('xss')</SCRIPT>") is False
            assert validate_xss_input("JavaScript:alert('xss')") is False
            assert validate_xss_input("OnClick=alert('xss')") is False


class TestSafeLikePattern:
    """Test cases for safe_like_pattern function."""
    
    def test_escape_percent(self):
        """Test escaping of percent character."""
        assert safe_like_pattern("100%") == "100\\%"
        assert safe_like_pattern("%test%") == "\\%test\\%"
    
    def test_escape_underscore(self):
        """Test escaping of underscore character."""
        assert safe_like_pattern("test_data") == "test\\_data"
        assert safe_like_pattern("_private") == "\\_private"
    
    def test_escape_backslash(self):
        """Test escaping of backslash character."""
        assert safe_like_pattern("path\\file") == "path\\\\file"
        assert safe_like_pattern("\\escape") == "\\\\escape"
    
    def test_escape_bracket(self):
        """Test escaping of bracket character."""
        assert safe_like_pattern("[test]") == "\\[test]"
        assert safe_like_pattern("array[0]") == "array\\[0]"
    
    def test_combined_escaping(self):
        """Test combined character escaping."""
        assert safe_like_pattern("test_%\\[data]") == "test\\_\\%\\\\\\[data]"
    
    def test_no_escaping_needed(self):
        """Test input that needs no escaping."""
        assert safe_like_pattern("normal text") == "normal text"
        assert safe_like_pattern("user@example.com") == "user@example.com"


class TestValidateUuid:
    """Test cases for validate_uuid function."""
    
    def test_valid_uuid(self):
        """Test validation of valid UUIDs."""
        assert validate_uuid("550e8400-e29b-41d4-a716-446655440000") is True
        assert validate_uuid("6ba7b810-9dad-11d1-80b4-00c04fd430c8") is True
        assert validate_uuid("00000000-0000-0000-0000-000000000000") is True
    
    def test_invalid_uuid(self):
        """Test validation of invalid UUIDs."""
        assert validate_uuid("not-a-uuid") is False
        assert validate_uuid("550e8400-e29b-41d4-a716") is False
        assert validate_uuid("550e8400e29b41d4a716446655440000") is False
        assert validate_uuid("") is False
        assert validate_uuid("xyz-xyz-xyz-xyz-xyz") is False
    
    def test_case_insensitive(self):
        """Test case insensitive UUID validation."""
        assert validate_uuid("550E8400-E29B-41D4-A716-446655440000") is True
        assert validate_uuid("550e8400-E29B-41d4-A716-446655440000") is True


class TestValidateEmail:
    """Test cases for validate_email function."""
    
    def test_valid_emails(self):
        """Test validation of valid email addresses."""
        assert validate_email("user@example.com") is True
        assert validate_email("test.user@example.co.uk") is True
        assert validate_email("user+tag@example.com") is True
        assert validate_email("user_name@example-domain.com") is True
        assert validate_email("123@example.com") is True
    
    def test_invalid_emails(self):
        """Test validation of invalid email addresses."""
        assert validate_email("not-an-email") is False
        assert validate_email("@example.com") is False
        assert validate_email("user@") is False
        assert validate_email("user@.com") is False
        assert validate_email("user@example") is False
        assert validate_email("") is False
        assert validate_email("user @example.com") is False
        assert validate_email("user@exam ple.com") is False


class TestValidateSlug:
    """Test cases for validate_slug function."""
    
    def test_valid_slugs(self):
        """Test validation of valid slugs."""
        assert validate_slug("valid-slug") is True
        assert validate_slug("product-123") is True
        assert validate_slug("test") is True
        assert validate_slug("a-b-c-d") is True
        assert validate_slug("123-456") is True
    
    def test_invalid_slugs(self):
        """Test validation of invalid slugs."""
        assert validate_slug("Invalid-Slug") is False  # Uppercase
        assert validate_slug("invalid slug") is False  # Space
        assert validate_slug("invalid_slug") is False  # Underscore
        assert validate_slug("-invalid") is False  # Leading hyphen
        assert validate_slug("invalid-") is False  # Trailing hyphen
        assert validate_slug("") is False
        assert validate_slug("invalid--slug") is False  # Double hyphen
    
    def test_case_conversion(self):
        """Test slug validation with case conversion."""
        assert validate_slug("TEST") is False  # Uppercase detected as invalid
        assert validate_slug("test") is True  # Lowercase is valid


class TestSafeQueryParameters:
    """Test cases for safe_query_parameters function."""
    
    def test_string_sanitization(self):
        """Test sanitization of string parameters."""
        params = {"name": "<script>alert('xss')</script>"}
        result = safe_query_parameters(params)
        assert "<script>" not in result["name"]
    
    def test_list_sanitization(self):
        """Test sanitization of list parameters."""
        params = {"tags": ["<b>tag1</b>", "tag2", "<script>tag3</script>"]}
        result = safe_query_parameters(params)
        assert all("<" not in tag for tag in result["tags"])
    
    def test_tuple_sanitization(self):
        """Test sanitization of tuple parameters."""
        params = {"ids": ("id1", "<script>id2</script>", "id3")}
        result = safe_query_parameters(params)
        assert all("<script>" not in id for id in result["ids"])
    
    def test_non_string_preservation(self):
        """Test preservation of non-string types."""
        params = {
            "page": 1,
            "limit": 20,
            "active": True,
            "price": 99.99,
            "data": None
        }
        result = safe_query_parameters(params)
        assert result["page"] == 1
        assert result["limit"] == 20
        assert result["active"] is True
        assert result["price"] == 99.99
        assert result["data"] is None
    
    def test_mixed_parameters(self):
        """Test mixed parameter types."""
        params = {
            "name": "<b>test</b>",
            "age": 25,
            "tags": ["tag1", "<script>tag2</script>"],
            "active": True
        }
        result = safe_query_parameters(params)
        assert "<b>" not in result["name"]
        assert result["age"] == 25
        assert all("<script>" not in tag for tag in result["tags"])
        assert result["active"] is True


class TestSecureQueryBuilder:
    """Test cases for SecureQueryBuilder class."""
    
    def test_validate_column_name(self):
        """Test column name validation."""
        allowed = ["id", "name", "created_at", "updated_at"]
        
        assert SecureQueryBuilder.validate_column_name("name", allowed) is True
        assert SecureQueryBuilder.validate_column_name("created_at", allowed) is True
        assert SecureQueryBuilder.validate_column_name("invalid", allowed) is False
        assert SecureQueryBuilder.validate_column_name("", allowed) is False
    
    def test_validate_table_name(self):
        """Test table name validation."""
        allowed = ["users", "products", "orders"]
        
        assert SecureQueryBuilder.validate_table_name("users", allowed) is True
        assert SecureQueryBuilder.validate_table_name("products", allowed) is True
        assert SecureQueryBuilder.validate_table_name("invalid", allowed) is False
        assert SecureQueryBuilder.validate_table_name("", allowed) is False
    
    def test_build_safe_order_by_valid(self):
        """Test building safe ORDER BY clause with valid input."""
        mock_query = MagicMock(spec=Select)
        mock_query.order_by = MagicMock(return_value=mock_query)
        
        allowed_columns = ["id", "name", "created_at"]
        
        # Test ascending order
        result = SecureQueryBuilder.build_safe_order_by(
            mock_query, "name asc", allowed_columns
        )
        mock_query.order_by.assert_called_once()
        
        # Test descending order
        mock_query.reset_mock()
        result = SecureQueryBuilder.build_safe_order_by(
            mock_query, "created_at desc", allowed_columns
        )
        mock_query.order_by.assert_called_once()
        
        # Test default ascending when direction not specified
        mock_query.reset_mock()
        result = SecureQueryBuilder.build_safe_order_by(
            mock_query, "id", allowed_columns
        )
        mock_query.order_by.assert_called_once()
    
    def test_build_safe_order_by_invalid(self):
        """Test building safe ORDER BY clause with invalid input."""
        mock_query = MagicMock(spec=Select)
        allowed_columns = ["id", "name", "created_at"]
        
        with patch('app.core.security_utils.logger') as mock_logger:
            # Invalid column
            result = SecureQueryBuilder.build_safe_order_by(
                mock_query, "invalid_column desc", allowed_columns
            )
            mock_logger.warning.assert_called()
            assert result == mock_query  # Returns original query
            
            # Invalid direction
            mock_logger.reset_mock()
            result = SecureQueryBuilder.build_safe_order_by(
                mock_query, "name invalid_dir", allowed_columns
            )
            mock_logger.warning.assert_called()
    
    def test_build_safe_order_by_empty(self):
        """Test building safe ORDER BY clause with empty input."""
        mock_query = MagicMock(spec=Select)
        allowed_columns = ["id", "name"]
        
        # Empty string
        result = SecureQueryBuilder.build_safe_order_by(
            mock_query, "", allowed_columns
        )
        assert result == mock_query
        
        # None
        result = SecureQueryBuilder.build_safe_order_by(
            mock_query, None, allowed_columns
        )
        assert result == mock_query
    
    def test_build_safe_filter_valid(self):
        """Test building safe WHERE clause with valid filters."""
        mock_query = MagicMock(spec=Select)
        mock_query.where = MagicMock(return_value=mock_query)
        
        allowed_columns = ["id", "name", "status"]
        
        # Single value filter
        filters = {"name": "test"}
        result = SecureQueryBuilder.build_safe_filter(
            mock_query, filters, allowed_columns
        )
        mock_query.where.assert_called()
        
        # List value filter
        mock_query.reset_mock()
        filters = {"status": ["active", "pending"]}
        result = SecureQueryBuilder.build_safe_filter(
            mock_query, filters, allowed_columns
        )
        mock_query.where.assert_called()
    
    def test_build_safe_filter_invalid(self):
        """Test building safe WHERE clause with invalid filters."""
        mock_query = MagicMock(spec=Select)
        allowed_columns = ["id", "name", "status"]
        
        with patch('app.core.security_utils.logger') as mock_logger:
            # Invalid column
            filters = {"invalid_column": "value"}
            result = SecureQueryBuilder.build_safe_filter(
                mock_query, filters, allowed_columns
            )
            mock_logger.warning.assert_called()
            assert result == mock_query
    
    def test_build_safe_filter_none_values(self):
        """Test building safe WHERE clause with None values."""
        mock_query = MagicMock(spec=Select)
        mock_query.where = MagicMock(return_value=mock_query)
        
        allowed_columns = ["id", "name", "status"]
        
        # None values should be skipped
        filters = {"name": "test", "status": None}
        result = SecureQueryBuilder.build_safe_filter(
            mock_query, filters, allowed_columns
        )
        
        # Only one call for non-None value
        assert mock_query.where.call_count == 1
    
    def test_build_safe_filter_multiple(self):
        """Test building safe WHERE clause with multiple filters."""
        mock_query = MagicMock(spec=Select)
        mock_query.where = MagicMock(return_value=mock_query)
        
        allowed_columns = ["id", "name", "status", "type"]
        
        filters = {
            "name": "test",
            "status": "active",
            "type": ["type1", "type2"]
        }
        result = SecureQueryBuilder.build_safe_filter(
            mock_query, filters, allowed_columns
        )
        
        # Should be called 3 times (once for each filter)
        assert mock_query.where.call_count == 3


class TestSecurityPatterns:
    """Test the security patterns themselves."""
    
    def test_sql_injection_patterns_coverage(self):
        """Test that SQL injection patterns cover common attacks."""
        test_cases = [
            "SELECT * FROM users",
            "INSERT INTO users VALUES",
            "UPDATE users SET",
            "DELETE FROM users",
            "DROP TABLE users",
            "UNION SELECT",
            "ALTER TABLE",
            "CREATE TABLE",
            "EXEC sp_",
            "EXECUTE(",
            "-- comment",
            "# comment",
            "/* comment */",
            "OR 1=1",
            "AND 1=1",
            "'; DROP",
            "SLEEP(5)",
            "BENCHMARK(",
            "WAITFOR DELAY"
        ]
        
        for test_case in test_cases:
            matched = False
            for pattern in SQL_INJECTION_PATTERNS:
                if re.search(pattern, test_case, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Pattern not detected: {test_case}"
    
    def test_xss_patterns_coverage(self):
        """Test that XSS patterns cover common attacks."""
        test_cases = [
            "<script>alert('xss')</script>",
            "javascript:void(0)",
            "onclick=alert",
            "onmouseover=",
            "<iframe src=",
            "<embed src=",
            "<object data="
        ]
        
        for test_case in test_cases:
            matched = False
            for pattern in XSS_PATTERNS:
                if re.search(pattern, test_case, re.IGNORECASE):
                    matched = True
                    break
            assert matched, f"Pattern not detected: {test_case}"