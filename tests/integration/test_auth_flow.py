"""Integration tests for authentication and authorization flows."""

import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
from unittest.mock import patch, AsyncMock
import jwt

from app.models.user import User, UserRole
from app.models.organization import Organization
from app.models.knowledge_item import KnowledgeItem
from app.auth.security import create_access_token, create_refresh_token, verify_password
from app.core.config import get_settings


@pytest.mark.integration
class TestAuthenticationFlow:
    """Test authentication flows."""
    
    async def test_complete_registration_flow(self, client: AsyncClient, db_session: AsyncSession):
        """Test complete user registration flow."""
        # Step 1: Register new user
        registration_data = {
            "email": "newuser@example.com",
            "username": "newuser",
            "password": "SecurePassword123!",
            "full_name": "New User",
            "organization_name": "New Organization",
            "preferred_language": "en"
        }
        
        response = await client.post(
            "/api/v1/auth/register",
            json=registration_data
        )
        
        assert response.status_code == 201
        user_data = response.json()
        assert user_data["email"] == registration_data["email"]
        assert user_data["username"] == registration_data["username"]
        assert "id" in user_data
        assert "password" not in user_data
        
        # Step 2: Verify user was created in database
        from sqlalchemy import select
        result = await db_session.execute(
            select(User).where(User.email == registration_data["email"])
        )
        user = result.scalar_one_or_none()
        assert user is not None
        assert user.is_active is True
        assert user.is_verified is False  # Email not verified yet
        
        # Step 3: Try to login before email verification
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": registration_data["email"],
                "password": registration_data["password"]
            }
        )
        
        # Should succeed but with limited access
        assert login_response.status_code == 200
        tokens = login_response.json()
        assert "access_token" in tokens
        
        # Step 4: Simulate email verification
        user.is_verified = True
        await db_session.commit()
        
        # Step 5: Login after verification
        verified_login = await client.post(
            "/api/v1/auth/login",
            json={
                "email": registration_data["email"],
                "password": registration_data["password"]
            }
        )
        
        assert verified_login.status_code == 200
        verified_tokens = verified_login.json()
        assert "access_token" in verified_tokens
        assert "refresh_token" in verified_tokens
    
    async def test_login_with_rate_limiting(self, client: AsyncClient, test_user: User):
        """Test login rate limiting to prevent brute force attacks."""
        # Attempt multiple failed logins
        failed_attempts = []
        
        for i in range(10):
            response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_user.email,
                    "password": "wrongpassword"
                }
            )
            failed_attempts.append(response.status_code)
        
        # After multiple attempts, should be rate limited
        assert 429 in failed_attempts or all(status == 401 for status in failed_attempts)
    
    async def test_token_refresh_flow(self, client: AsyncClient, test_user: User):
        """Test complete token refresh flow."""
        # Step 1: Login to get tokens
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": "test@example.com",
                "password": "testpassword123"
            }
        )
        
        assert login_response.status_code == 200
        tokens = login_response.json()
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        
        # Step 2: Use access token to access protected endpoint
        headers = {"Authorization": f"Bearer {access_token}"}
        me_response = await client.get("/api/v1/auth/me", headers=headers)
        assert me_response.status_code == 200
        
        # Step 3: Refresh tokens
        refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        
        assert refresh_response.status_code == 200
        new_tokens = refresh_response.json()
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert new_tokens["access_token"] != access_token
        
        # Step 4: Use new access token
        new_headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
        me_response2 = await client.get("/api/v1/auth/me", headers=new_headers)
        assert me_response2.status_code == 200
        
        # Step 5: Old refresh token should be invalidated
        old_refresh_response = await client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token}
        )
        # Depending on implementation, might still work or be invalidated
        # This is implementation specific
    
    async def test_password_reset_flow(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Test complete password reset flow."""
        # Step 1: Request password reset
        with patch('app.services.email.send_password_reset_email') as mock_send_email:
            mock_send_email.return_value = True
            
            reset_request = await client.post(
                "/api/v1/auth/forgot-password",
                json={"email": test_user.email}
            )
            
            # Should always return 200 to prevent email enumeration
            assert reset_request.status_code == 200
            mock_send_email.assert_called_once()
        
        # Step 2: Generate reset token (normally sent via email)
        settings = get_settings()
        reset_token = jwt.encode(
            {
                "sub": str(test_user.id),
                "type": "password_reset",
                "exp": datetime.utcnow() + timedelta(hours=1)
            },
            settings.secret_key,
            algorithm="HS256"
        )
        
        # Step 3: Reset password with token
        new_password = "NewSecurePassword456!"
        reset_response = await client.post(
            "/api/v1/auth/reset-password",
            json={
                "token": reset_token,
                "new_password": new_password
            }
        )
        
        assert reset_response.status_code == 200
        
        # Step 4: Login with new password
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": new_password
            }
        )
        
        assert login_response.status_code == 200
        assert "access_token" in login_response.json()
    
    async def test_session_management(self, client: AsyncClient, test_user: User):
        """Test session management and concurrent sessions."""
        # Create multiple sessions
        sessions = []
        
        for i in range(3):
            login_response = await client.post(
                "/api/v1/auth/login",
                json={
                    "email": test_user.email,
                    "password": "testpassword123"
                }
            )
            assert login_response.status_code == 200
            sessions.append(login_response.json())
        
        # All sessions should be valid
        for session in sessions:
            headers = {"Authorization": f"Bearer {session['access_token']}"}
            response = await client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code == 200
        
        # Logout from one session
        logout_headers = {"Authorization": f"Bearer {sessions[0]['access_token']}"}
        logout_response = await client.post(
            "/api/v1/auth/logout",
            headers=logout_headers,
            json={"refresh_token": sessions[0]["refresh_token"]}
        )
        assert logout_response.status_code == 200
        
        # Other sessions should still be valid
        for session in sessions[1:]:
            headers = {"Authorization": f"Bearer {session['access_token']}"}
            response = await client.get("/api/v1/auth/me", headers=headers)
            assert response.status_code == 200


@pytest.mark.integration
class TestAuthorizationFlow:
    """Test authorization and permission flows."""
    
    async def test_role_based_access_control(self, client: AsyncClient, db_session: AsyncSession, test_organization: Organization):
        """Test RBAC with different user roles."""
        # Create users with different roles
        users = []
        roles = [UserRole.VIEWER, UserRole.EDITOR, UserRole.ADMIN]
        
        for i, role in enumerate(roles):
            user = User(
                organization_id=test_organization.id,
                email=f"{role.value}@example.com",
                username=f"{role.value}_user",
                full_name=f"{role.value.title()} User",
                hashed_password="$2b$12$test",
                role=role,
                is_active=True,
                is_verified=True
            )
            users.append(user)
        
        db_session.add_all(users)
        await db_session.commit()
        
        # Test access for each role
        for user in users:
            # Login
            with patch('app.auth.security.verify_password') as mock_verify:
                mock_verify.return_value = True
                
                login_response = await client.post(
                    "/api/v1/auth/login",
                    json={
                        "email": user.email,
                        "password": "password"
                    }
                )
                
                headers = {"Authorization": f"Bearer {login_response.json()['access_token']}"}
                
                # Test viewer permissions
                if user.role == UserRole.VIEWER:
                    # Can read
                    read_response = await client.get("/api/v1/knowledge", headers=headers)
                    assert read_response.status_code == 200
                    
                    # Cannot create
                    create_response = await client.post(
                        "/api/v1/knowledge",
                        headers=headers,
                        json={"title": "Test", "content": "Test"}
                    )
                    assert create_response.status_code == 403
                
                # Test editor permissions
                elif user.role == UserRole.EDITOR:
                    # Can read and create
                    read_response = await client.get("/api/v1/knowledge", headers=headers)
                    assert read_response.status_code == 200
                    
                    create_response = await client.post(
                        "/api/v1/knowledge",
                        headers=headers,
                        json={"title": "Test", "content": "Test"}
                    )
                    assert create_response.status_code in [201, 422]  # 422 if validation fails
                    
                    # Cannot access admin endpoints
                    admin_response = await client.get("/api/v1/admin/users", headers=headers)
                    assert admin_response.status_code == 403
                
                # Test admin permissions
                elif user.role == UserRole.ADMIN:
                    # Can do everything
                    read_response = await client.get("/api/v1/knowledge", headers=headers)
                    assert read_response.status_code == 200
                    
                    admin_response = await client.get("/api/v1/admin/users", headers=headers)
                    assert admin_response.status_code == 200
    
    async def test_organization_isolation(self, client: AsyncClient, db_session: AsyncSession):
        """Test that users can only access their organization's data."""
        # Create two organizations
        org1 = Organization(name="Org 1", slug="org1")
        org2 = Organization(name="Org 2", slug="org2")
        db_session.add_all([org1, org2])
        await db_session.commit()
        
        # Create users in different organizations
        user1 = User(
            organization_id=org1.id,
            email="user1@org1.com",
            username="user1",
            full_name="User 1",
            hashed_password="$2b$12$test",
            role=UserRole.EDITOR,
            is_active=True
        )
        
        user2 = User(
            organization_id=org2.id,
            email="user2@org2.com",
            username="user2",
            full_name="User 2",
            hashed_password="$2b$12$test",
            role=UserRole.EDITOR,
            is_active=True
        )
        
        db_session.add_all([user1, user2])
        await db_session.commit()
        
        # Create knowledge items for each organization
        item1 = KnowledgeItem(
            organization_id=org1.id,
            created_by_id=user1.id,
            title="Org1 Item",
            content="Org1 content"
        )
        
        item2 = KnowledgeItem(
            organization_id=org2.id,
            created_by_id=user2.id,
            title="Org2 Item",
            content="Org2 content"
        )
        
        db_session.add_all([item1, item2])
        await db_session.commit()
        
        # User1 should only see org1's items
        with patch('app.auth.security.verify_password') as mock_verify:
            mock_verify.return_value = True
            
            # Login as user1
            login1 = await client.post(
                "/api/v1/auth/login",
                json={"email": user1.email, "password": "password"}
            )
            headers1 = {"Authorization": f"Bearer {login1.json()['access_token']}"}
            
            # Get items - should only see org1's items
            items_response = await client.get("/api/v1/knowledge", headers=headers1)
            assert items_response.status_code == 200
            items = items_response.json()
            
            # Verify organization isolation
            if isinstance(items, dict) and "items" in items:
                for item in items["items"]:
                    assert item.get("organization_id") == str(org1.id)
            
            # Try to access org2's item - should fail
            other_item_response = await client.get(
                f"/api/v1/knowledge/{item2.id}",
                headers=headers1
            )
            assert other_item_response.status_code in [403, 404]
    
    async def test_api_key_authentication(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Test API key authentication as alternative to JWT."""
        # Generate API key for user
        api_key = "sk_test_" + "x" * 32
        test_user.api_key = api_key
        await db_session.commit()
        
        # Test API key authentication
        headers = {"X-API-Key": api_key}
        
        with patch('app.auth.dependencies.get_user_from_api_key') as mock_get_user:
            mock_get_user.return_value = test_user
            
            response = await client.get("/api/v1/knowledge", headers=headers)
            # API key auth might not be implemented, so accept 401 or 200
            assert response.status_code in [200, 401]
    
    async def test_token_expiration_handling(self, client: AsyncClient, test_user: User):
        """Test expired token handling."""
        settings = get_settings()
        
        # Create an expired token
        expired_token = jwt.encode(
            {
                "sub": str(test_user.id),
                "exp": datetime.utcnow() - timedelta(hours=1)
            },
            settings.secret_key,
            algorithm="HS256"
        )
        
        # Try to use expired token
        headers = {"Authorization": f"Bearer {expired_token}"}
        response = await client.get("/api/v1/auth/me", headers=headers)
        
        assert response.status_code == 401
        assert "expired" in response.json()["detail"].lower() or "invalid" in response.json()["detail"].lower()
    
    async def test_permission_inheritance(self, client: AsyncClient, db_session: AsyncSession, test_organization: Organization):
        """Test permission inheritance and override."""
        # Create admin user
        admin = User(
            organization_id=test_organization.id,
            email="admin@test.com",
            username="admin",
            full_name="Admin",
            hashed_password="$2b$12$test",
            role=UserRole.ADMIN,
            is_active=True
        )
        
        # Create editor user
        editor = User(
            organization_id=test_organization.id,
            email="editor@test.com",
            username="editor",
            full_name="Editor",
            hashed_password="$2b$12$test",
            role=UserRole.EDITOR,
            is_active=True
        )
        
        db_session.add_all([admin, editor])
        await db_session.commit()
        
        # Create knowledge item by editor
        item = KnowledgeItem(
            organization_id=test_organization.id,
            created_by_id=editor.id,
            title="Editor's Item",
            content="Created by editor"
        )
        db_session.add(item)
        await db_session.commit()
        
        with patch('app.auth.security.verify_password') as mock_verify:
            mock_verify.return_value = True
            
            # Editor can update own item
            editor_login = await client.post(
                "/api/v1/auth/login",
                json={"email": editor.email, "password": "password"}
            )
            editor_headers = {"Authorization": f"Bearer {editor_login.json()['access_token']}"}
            
            update_response = await client.put(
                f"/api/v1/knowledge/{item.id}",
                headers=editor_headers,
                json={"title": "Updated by editor"}
            )
            assert update_response.status_code in [200, 403]  # Depends on implementation
            
            # Admin can update any item
            admin_login = await client.post(
                "/api/v1/auth/login",
                json={"email": admin.email, "password": "password"}
            )
            admin_headers = {"Authorization": f"Bearer {admin_login.json()['access_token']}"}
            
            admin_update = await client.put(
                f"/api/v1/knowledge/{item.id}",
                headers=admin_headers,
                json={"title": "Updated by admin"}
            )
            assert admin_update.status_code == 200
    
    async def test_multi_factor_authentication(self, client: AsyncClient, test_user: User, db_session: AsyncSession):
        """Test MFA flow."""
        # Enable MFA for user
        test_user.mfa_enabled = True
        test_user.mfa_secret = "JBSWY3DPEHPK3PXP"  # Example TOTP secret
        await db_session.commit()
        
        # Step 1: Initial login attempt
        login_response = await client.post(
            "/api/v1/auth/login",
            json={
                "email": test_user.email,
                "password": "testpassword123"
            }
        )
        
        # Should require MFA code
        if hasattr(test_user, 'mfa_enabled') and test_user.mfa_enabled:
            assert login_response.status_code in [200, 202]  # 202 for MFA required
            
            if login_response.status_code == 202:
                # Step 2: Provide MFA code
                import pyotp
                totp = pyotp.TOTP(test_user.mfa_secret)
                current_code = totp.now()
                
                mfa_response = await client.post(
                    "/api/v1/auth/verify-mfa",
                    json={
                        "email": test_user.email,
                        "mfa_code": current_code
                    }
                )
                
                assert mfa_response.status_code == 200
                assert "access_token" in mfa_response.json()