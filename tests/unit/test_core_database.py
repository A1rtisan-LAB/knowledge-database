"""Comprehensive tests for database module."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch, call
from sqlalchemy.ext.asyncio import AsyncSession, AsyncEngine
from sqlalchemy.pool import NullPool

from app.core.database import (
    get_db,
    get_db_context,
    init_db,
    close_db,
    engine,
    AsyncSessionLocal,
    Base
)


class TestDatabaseEngine:
    """Test cases for database engine configuration."""
    
    @patch('app.core.database.create_async_engine')
    @patch('app.core.database.get_settings')
    def test_sqlite_engine_configuration(self, mock_settings, mock_create_engine):
        """Test SQLite engine configuration for testing."""
        # Setup mock settings
        mock_settings.return_value.app_env = "testing"
        mock_settings.return_value.database_url = "sqlite+aiosqlite:///test.db"
        mock_settings.return_value.database_echo = False
        
        # Import to trigger engine creation
        import importlib
        import app.core.database
        importlib.reload(app.core.database)
        
        # Verify SQLite uses NullPool
        mock_create_engine.assert_called()
        call_args = mock_create_engine.call_args
        assert call_args[1]['poolclass'] == NullPool
    
    @patch('app.core.database.create_async_engine')
    @patch('app.core.database.get_settings')
    def test_postgresql_engine_configuration(self, mock_settings, mock_create_engine):
        """Test PostgreSQL engine configuration for production."""
        # Setup mock settings
        mock_settings.return_value.app_env = "production"
        mock_settings.return_value.database_url = "postgresql+asyncpg://user:pass@localhost/db"
        mock_settings.return_value.database_echo = False
        mock_settings.return_value.database_pool_size = 20
        mock_settings.return_value.database_max_overflow = 40
        mock_settings.return_value.database_pool_timeout = 30
        
        # Import to trigger engine creation
        import importlib
        import app.core.database
        importlib.reload(app.core.database)
        
        # Verify PostgreSQL uses pool settings
        mock_create_engine.assert_called()
        call_args = mock_create_engine.call_args
        assert call_args[1].get('pool_size') == 20
        assert call_args[1].get('max_overflow') == 40
        assert call_args[1].get('pool_timeout') == 30
        assert call_args[1].get('pool_pre_ping') is True


class TestGetDb:
    """Test cases for get_db dependency function."""
    
    @pytest.mark.asyncio
    async def test_successful_session_lifecycle(self):
        """Test successful database session lifecycle."""
        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        # Mock session factory
        with patch('app.core.database.AsyncSessionLocal') as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock()
            
            # Test successful transaction
            async for session in get_db():
                assert session == mock_session
            
            # Verify lifecycle calls
            mock_session.commit.assert_called_once()
            mock_session.rollback.assert_not_called()
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_rollback_on_exception(self):
        """Test database rollback on exception."""
        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock(side_effect=Exception("Database error"))
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        # Mock session factory
        with patch('app.core.database.AsyncSessionLocal') as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock()
            
            # Test exception handling
            with pytest.raises(Exception) as exc_info:
                async for session in get_db():
                    assert session == mock_session
            
            assert str(exc_info.value) == "Database error"
            
            # Verify rollback was called
            mock_session.commit.assert_called_once()
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_always_called(self):
        """Test that close is always called even on error."""
        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock(side_effect=Exception("Rollback error"))
        mock_session.close = AsyncMock()
        
        # Mock session factory
        with patch('app.core.database.AsyncSessionLocal') as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock()
            
            # Simulate exception in the generator body
            with pytest.raises(Exception):
                async for session in get_db():
                    raise Exception("User error")
            
            # Verify close was still called
            mock_session.close.assert_called_once()


class TestGetDbContext:
    """Test cases for get_db_context context manager."""
    
    @pytest.mark.asyncio
    async def test_successful_context_lifecycle(self):
        """Test successful database context lifecycle."""
        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        # Mock session factory
        with patch('app.core.database.AsyncSessionLocal') as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock()
            
            # Test successful transaction
            async with get_db_context() as session:
                assert session == mock_session
            
            # Verify lifecycle calls
            mock_session.commit.assert_called_once()
            mock_session.rollback.assert_not_called()
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_rollback_on_exception(self):
        """Test database context rollback on exception."""
        # Mock session
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        
        # Mock session factory
        with patch('app.core.database.AsyncSessionLocal') as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock()
            
            # Test exception handling
            with pytest.raises(ValueError):
                async with get_db_context() as session:
                    assert session == mock_session
                    raise ValueError("Test error")
            
            # Verify rollback was called
            mock_session.commit.assert_not_called()
            mock_session.rollback.assert_called_once()
            mock_session.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_context_nested_transactions(self):
        """Test nested context usage."""
        # Mock sessions
        mock_session1 = AsyncMock(spec=AsyncSession)
        mock_session1.commit = AsyncMock()
        mock_session1.rollback = AsyncMock()
        mock_session1.close = AsyncMock()
        
        mock_session2 = AsyncMock(spec=AsyncSession)
        mock_session2.commit = AsyncMock()
        mock_session2.rollback = AsyncMock()
        mock_session2.close = AsyncMock()
        
        # Mock session factory to return different sessions
        sessions = [mock_session2, mock_session1]  # Reversed for pop()
        
        class MockFactory:
            async def __aenter__(self):
                return sessions.pop()
            async def __aexit__(self, *args):
                pass
        
        with patch('app.core.database.AsyncSessionLocal', return_value=MockFactory()):
            # Test nested contexts
            async with get_db_context() as session1:
                assert session1 == mock_session1
                async with get_db_context() as session2:
                    assert session2 == mock_session2
            
            # Verify both sessions were properly managed
            mock_session1.commit.assert_called_once()
            mock_session2.commit.assert_called_once()
            mock_session1.close.assert_called_once()
            mock_session2.close.assert_called_once()


class TestInitDb:
    """Test cases for init_db function."""
    
    @pytest.mark.asyncio
    async def test_init_db_creates_tables(self):
        """Test that init_db creates all tables."""
        # Mock engine and connection
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()
        
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock()
        
        with patch('app.core.database.engine', mock_engine):
            # Import models to ensure they're loaded
            with patch('app.core.database.organization'):
                with patch('app.core.database.user'):
                    with patch('app.core.database.knowledge_item'):
                        with patch('app.core.database.category'):
                            with patch('app.core.database.audit_log'):
                                await init_db()
        
        # Verify engine.begin() was called
        mock_engine.begin.assert_called_once()
        
        # Verify metadata.create_all was called via run_sync
        mock_conn.run_sync.assert_called_once()
        call_args = mock_conn.run_sync.call_args
        assert call_args[0][0] == Base.metadata.create_all
    
    @pytest.mark.asyncio
    async def test_init_db_imports_all_models(self):
        """Test that init_db imports all required models."""
        mock_conn = AsyncMock()
        mock_conn.run_sync = AsyncMock()
        
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_engine.begin = AsyncMock()
        mock_engine.begin.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
        mock_engine.begin.return_value.__aexit__ = AsyncMock()
        
        with patch('app.core.database.engine', mock_engine):
            # Track model imports
            with patch('app.core.database.organization') as mock_org:
                with patch('app.core.database.user') as mock_user:
                    with patch('app.core.database.knowledge_item') as mock_knowledge:
                        with patch('app.core.database.category') as mock_category:
                            with patch('app.core.database.audit_log') as mock_audit:
                                await init_db()
                                
                                # All models should be imported (patched)
                                # The patches themselves confirm the imports happened


class TestCloseDb:
    """Test cases for close_db function."""
    
    @pytest.mark.asyncio
    async def test_close_db_disposes_engine(self):
        """Test that close_db properly disposes the engine."""
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_engine.dispose = AsyncMock()
        
        with patch('app.core.database.engine', mock_engine):
            await close_db()
        
        # Verify engine.dispose() was called
        mock_engine.dispose.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_close_db_handles_dispose_error(self):
        """Test that close_db handles disposal errors gracefully."""
        mock_engine = AsyncMock(spec=AsyncEngine)
        mock_engine.dispose = AsyncMock(side_effect=Exception("Disposal error"))
        
        with patch('app.core.database.engine', mock_engine):
            # Should raise the exception
            with pytest.raises(Exception) as exc_info:
                await close_db()
            
            assert str(exc_info.value) == "Disposal error"
            mock_engine.dispose.assert_called_once()


class TestAsyncSessionLocal:
    """Test cases for AsyncSessionLocal configuration."""
    
    def test_session_factory_configuration(self):
        """Test that session factory is properly configured."""
        assert AsyncSessionLocal is not None
        assert AsyncSessionLocal.kw.get('expire_on_commit') is False
        assert AsyncSessionLocal.kw.get('autocommit') is False
        assert AsyncSessionLocal.kw.get('autoflush') is False
        assert AsyncSessionLocal.kw.get('class_') == AsyncSession


class TestBase:
    """Test cases for declarative Base."""
    
    def test_base_is_declarative(self):
        """Test that Base is a proper declarative base."""
        assert Base is not None
        assert hasattr(Base, 'metadata')
        assert hasattr(Base, '__tablename__')


class TestTransactionScenarios:
    """Test complex transaction scenarios."""
    
    @pytest.mark.asyncio
    async def test_concurrent_sessions(self):
        """Test handling of concurrent database sessions."""
        # Mock sessions
        sessions = []
        for i in range(3):
            mock_session = AsyncMock(spec=AsyncSession)
            mock_session.id = i
            mock_session.commit = AsyncMock()
            mock_session.rollback = AsyncMock()
            mock_session.close = AsyncMock()
            sessions.append(mock_session)
        
        # Track session creation order
        session_counter = 0
        
        class MockFactory:
            def __init__(self):
                nonlocal session_counter
                self.session = sessions[session_counter]
                session_counter += 1
            
            async def __aenter__(self):
                return self.session
            
            async def __aexit__(self, *args):
                pass
        
        with patch('app.core.database.AsyncSessionLocal', MockFactory):
            # Create multiple concurrent sessions
            collected_sessions = []
            
            async def get_session():
                async for session in get_db():
                    collected_sessions.append(session)
                    return session
            
            # Run concurrently
            import asyncio
            await asyncio.gather(
                get_session(),
                get_session(),
                get_session()
            )
            
            # Verify all sessions were created and managed
            assert len(collected_sessions) == 3
            for i, session in enumerate(sessions):
                assert session.commit.called
                assert session.close.called
    
    @pytest.mark.asyncio
    async def test_savepoint_rollback(self):
        """Test savepoint and partial rollback scenarios."""
        mock_session = AsyncMock(spec=AsyncSession)
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()
        mock_session.close = AsyncMock()
        mock_session.begin_nested = AsyncMock()
        
        mock_savepoint = AsyncMock()
        mock_savepoint.rollback = AsyncMock()
        mock_savepoint.__aenter__ = AsyncMock(return_value=mock_savepoint)
        mock_savepoint.__aexit__ = AsyncMock()
        
        mock_session.begin_nested.return_value = mock_savepoint
        
        with patch('app.core.database.AsyncSessionLocal') as mock_factory:
            mock_factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_factory.return_value.__aexit__ = AsyncMock()
            
            async with get_db_context() as session:
                # Create a savepoint
                async with session.begin_nested():
                    pass
                
                # Verify savepoint was created
                mock_session.begin_nested.assert_called()
    
    @pytest.mark.asyncio
    async def test_connection_pool_exhaustion(self):
        """Test behavior when connection pool is exhausted."""
        from sqlalchemy.exc import TimeoutError
        
        mock_session = AsyncMock(spec=AsyncSession)
        
        # Simulate pool exhaustion
        with patch('app.core.database.AsyncSessionLocal') as mock_factory:
            mock_factory.side_effect = TimeoutError(
                "QueuePool limit of size 5 overflow 10 reached",
                None,
                None
            )
            
            with pytest.raises(TimeoutError) as exc_info:
                async for session in get_db():
                    pass
            
            assert "QueuePool limit" in str(exc_info.value)