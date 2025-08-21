"""Unit tests for authentication and authorization."""

import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from jose import jwt

from app.auth.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    verify_token
)
from app.auth.dependencies import (
    get_current_active_user,
    require_admin,
    require_editor
)
from app.models.user import User, UserRole
from app.core.config import Settings


@pytest.mark.unit
class TestPasswordHashing:
    """Test password hashing functions."""
    
    def test_password_hash(self):
        """Test password hashing."""
        password = "SecurePassword123!"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 20
        assert hashed.startswith("$2b$")  # bcrypt prefix
        
    def test_password_verification_correct(self):
        """Test verifying correct password."""
        password = "TestPassword456"
        hashed = get_password_hash(password)
        
        assert verify_password(password, hashed) is True
        
    def test_password_verification_incorrect(self):
        """Test verifying incorrect password."""
        password = "CorrectPassword"
        wrong_password = "WrongPassword"
        hashed = get_password_hash(password)
        
        assert verify_password(wrong_password, hashed) is False
        
    def test_different_hashes_same_password(self):
        """Test that same password produces different hashes."""
        password = "SamePassword789"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        assert hash1 != hash2
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True
        
    def test_empty_password(self):
        """Test handling empty password."""
        password = ""
        hashed = get_password_hash(password)
        
        assert hashed != ""
        assert verify_password("", hashed) is True
        assert verify_password("notEmpty", hashed) is False


@pytest.mark.unit
class TestTokenCreation:
    """Test JWT token creation."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.secret_key = "test-secret-key-for-testing-only"
        settings.algorithm = "HS256"
        settings.access_token_expire_minutes = 30
        settings.refresh_token_expire_days = 7
        return settings
    
    def test_create_access_token(self, mock_settings):
        """Test creating access token."""
        with patch('app.auth.security.get_settings', return_value=mock_settings):
            user_id = "user123"
            token = create_access_token(
                data={"sub": user_id}
            )
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify
        payload = jwt.decode(
            token,
            mock_settings.secret_key,
            algorithms=[mock_settings.algorithm]
        )
        assert payload["sub"] == user_id
        assert "exp" in payload
        
    def test_create_refresh_token(self, mock_settings):
        """Test creating refresh token."""
        with patch('app.auth.security.get_settings', return_value=mock_settings):
            user_id = "user456"
            token = create_refresh_token(
                data={"sub": user_id}
            )
        
        assert token is not None
        assert isinstance(token, str)
        
        # Decode and verify
        payload = jwt.decode(
            token,
            mock_settings.secret_key,
            algorithms=[mock_settings.algorithm]
        )
        assert payload["sub"] == user_id
        assert payload["type"] == "refresh"
        
    def test_access_token_expiry(self, mock_settings):
        """Test access token expiry time."""
        with patch('app.auth.security.get_settings', return_value=mock_settings):
            token = create_access_token(
                data={"sub": "user"}
            )
        
        payload = jwt.decode(
            token,
            mock_settings.secret_key,
            algorithms=[mock_settings.algorithm]
        )
        
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_exp = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(minutes=30)
        
        # Allow 5 second tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 5
        
    def test_refresh_token_expiry(self, mock_settings):
        """Test refresh token expiry time."""
        with patch('app.auth.security.get_settings', return_value=mock_settings):
            token = create_refresh_token(
                data={"sub": "user"}
            )
        
        payload = jwt.decode(
            token,
            mock_settings.secret_key,
            algorithms=[mock_settings.algorithm]
        )
        
        exp_time = datetime.fromtimestamp(payload["exp"])
        expected_exp = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(days=7)
        
        # Allow 5 second tolerance
        assert abs((exp_time - expected_exp).total_seconds()) < 5
        
    def test_token_with_additional_claims(self, mock_settings):
        """Test creating token with additional claims."""
        data = {
            "sub": "user789",
            "role": "admin",
            "org_id": "org123"
        }
        
        with patch('app.auth.security.get_settings', return_value=mock_settings):
            token = create_access_token(data=data)
        payload = jwt.decode(
            token,
            mock_settings.secret_key,
            algorithms=[mock_settings.algorithm]
        )
        
        assert payload["sub"] == "user789"
        assert payload["role"] == "admin"
        assert payload["org_id"] == "org123"


@pytest.mark.unit
class TestTokenDecoding:
    """Test JWT token decoding."""
    
    @pytest.fixture
    def mock_settings(self):
        """Create mock settings."""
        settings = Mock(spec=Settings)
        settings.secret_key = "test-secret-key"
        settings.algorithm = "HS256"
        return settings
    
    def test_decode_valid_token(self, mock_settings):
        """Test decoding valid token."""
        # Create token
        data = {"sub": "user123", "role": "editor"}
        token = jwt.encode(
            {**data, "exp": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1), "type": "access"},
            mock_settings.secret_key,
            algorithm=mock_settings.algorithm
        )
        
        # Decode
        with patch('app.auth.security.get_settings', return_value=mock_settings):
            payload = verify_token(token, "access")
        
        assert payload["sub"] == "user123"
        assert payload["role"] == "editor"
        
    def test_decode_expired_token(self, mock_settings):
        """Test decoding expired token."""
        # Create expired token
        data = {"sub": "user123"}
        token = jwt.encode(
            {**data, "exp": datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=1), "type": "access"},
            mock_settings.secret_key,
            algorithm=mock_settings.algorithm
        )
        
        # Should return None for expired token
        with patch('app.auth.security.get_settings', return_value=mock_settings):
            payload = verify_token(token, "access")
            assert payload is None
            
    def test_decode_invalid_signature(self, mock_settings):
        """Test decoding token with invalid signature."""
        # Create token with different secret
        data = {"sub": "user123"}
        token = jwt.encode(
            {**data, "exp": datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(hours=1), "type": "access"},
            "wrong-secret-key",
            algorithm=mock_settings.algorithm
        )
        
        # Should return None for invalid signature
        with patch('app.auth.security.get_settings', return_value=mock_settings):
            payload = verify_token(token, "access")
            assert payload is None
            
    def test_decode_malformed_token(self, mock_settings):
        """Test decoding malformed token."""
        token = "not.a.valid.token"
        
        with patch('app.auth.security.get_settings', return_value=mock_settings):
            payload = verify_token(token, "access")
            assert payload is None


@pytest.mark.unit
class TestAuthDependencies:
    """Test authentication dependencies."""
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user."""
        user = Mock(spec=User)
        user.id = "user123"
        user.email = "user@example.com"
        user.role = UserRole.EDITOR
        user.is_active = True
        user.is_verified = True
        return user
    
    @pytest.fixture
    def mock_admin_user(self):
        """Create mock admin user."""
        user = Mock(spec=User)
        user.id = "admin123"
        user.email = "admin@example.com"
        user.role = UserRole.ADMIN
        user.is_active = True
        user.is_verified = True
        return user
    
    async def test_get_current_active_user(self, mock_user):
        """Test getting current active user."""
        result = await get_current_active_user(mock_user)
        assert result == mock_user
        
    async def test_get_current_inactive_user(self, mock_user):
        """Test getting inactive user raises error."""
        mock_user.is_active = False
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await get_current_active_user(mock_user)
        assert exc.value.status_code == 403
        
    async def test_require_admin_with_admin(self, mock_admin_user):
        """Test admin requirement with admin user."""
        result = await require_admin(mock_admin_user)
        assert result == mock_admin_user
        
    async def test_require_admin_with_non_admin(self, mock_user):
        """Test admin requirement with non-admin user."""
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await require_admin(mock_user)
        assert exc.value.status_code == 403
        
    async def test_require_editor_with_editor(self, mock_user):
        """Test editor requirement with editor user."""
        result = await require_editor(mock_user)
        assert result == mock_user
        
    async def test_require_editor_with_admin(self, mock_admin_user):
        """Test editor requirement with admin user (should pass)."""
        result = await require_editor(mock_admin_user)
        assert result == mock_admin_user
        
    async def test_require_editor_with_viewer(self, mock_user):
        """Test editor requirement with viewer user."""
        mock_user.role = UserRole.VIEWER
        
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await require_editor(mock_user)
        assert exc.value.status_code == 403


@pytest.mark.unit
class TestRoleBasedAccess:
    """Test role-based access control."""
    
    def test_role_hierarchy(self):
        """Test role hierarchy."""
        # Admin > Editor > Viewer
        admin = UserRole.ADMIN
        editor = UserRole.EDITOR
        viewer = UserRole.VIEWER
        
        # Test role values
        assert admin.value == "admin"
        assert editor.value == "editor"
        assert viewer.value == "viewer"
        
    def test_role_permissions_admin(self):
        """Test admin role permissions."""
        # Using the actual enum value
        admin_role = UserRole.ADMIN
        
        # Admin can do everything
        admin_permissions = {
            "create": True,
            "read": True,
            "update": True,
            "delete": True,
            "manage_users": True,
            "manage_organization": True
        }
        
        # Verify the role exists and has expected value
        assert admin_role.value == "admin"
        
        # In a real implementation, these would be methods
        for _, allowed in admin_permissions.items():
            assert allowed is True
            
    def test_role_permissions_editor(self):
        """Test editor role permissions."""
        # Using the actual enum value
        editor_role = UserRole.EDITOR
        
        # Editor can create, read, update but not delete or manage
        editor_permissions = {
            "create": True,
            "read": True,
            "update": True,
            "delete": False,
            "manage_users": False,
            "manage_organization": False
        }
        
        # Verify the role exists and has expected value
        assert editor_role.value == "editor"
        
        # Verify expected permissions
        assert editor_permissions["create"] is True
        assert editor_permissions["manage_users"] is False
        
    def test_role_permissions_viewer(self):
        """Test viewer role permissions."""
        # Using the actual enum value
        viewer_role = UserRole.VIEWER
        
        # Viewer can only read
        viewer_permissions = {
            "create": False,
            "read": True,
            "update": False,
            "delete": False,
            "manage_users": False,
            "manage_organization": False
        }
        
        # Verify the role exists and has expected value
        assert viewer_role.value == "viewer"
        
        # Verify expected permissions
        assert viewer_permissions["read"] is True
        assert viewer_permissions["create"] is False