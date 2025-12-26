"""Tests for SessionStorage"""
import pytest
import json
import sys
import tempfile
import os
from pathlib import Path
from datetime import datetime, timedelta

# Setup path for imports
project_root = Path(__file__).parent.parent
mcp_path = project_root / "backend-mcp"
original_cwd = os.getcwd()
try:
    os.chdir(mcp_path)
    sys.path.insert(0, str(mcp_path))
    from app.services.session_storage import SessionStorage
    from app.core.exceptions import SessionStorageError
finally:
    os.chdir(original_cwd)
    if str(mcp_path) in sys.path:
        sys.path.remove(str(mcp_path))


class TestSessionStorage:
    """Test cases for SessionStorage"""
    
    @pytest.fixture
    def temp_db(self):
        """Create a temporary SQLite database file"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as f:
            db_path = f.name
        yield db_path
        # Cleanup
        if os.path.exists(db_path):
            os.unlink(db_path)
    
    @pytest.fixture
    def session_storage(self, temp_db):
        """Create SessionStorage instance with temporary database"""
        return SessionStorage(temp_db, default_ttl=3600)
    
    def test_init_success(self, temp_db):
        """Test successful initialization"""
        storage = SessionStorage(temp_db, default_ttl=3600)
        assert storage.default_ttl == 3600
        assert storage.db_path == temp_db
        # Verify database was created
        assert os.path.exists(temp_db)
    
    def test_init_creates_directory(self):
        """Test that initialization creates directory if needed"""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "subdir", "sessions.db")
            storage = SessionStorage(db_path, default_ttl=3600)
            assert os.path.exists(db_path)
            assert os.path.isdir(os.path.dirname(db_path))
    
    def test_create_session_success(self, session_storage):
        """Test successful session creation"""
        record_id = "001XXXX"
        context = {"test": "data"}
        
        session_id = session_storage.create_session(record_id, context)
        
        assert session_id is not None
        assert len(session_id) == 36  # UUID v4 length
        
        # Verify session was stored
        session_data = session_storage.get_session(session_id)
        assert session_data is not None
        assert session_data["record_id"] == record_id
        assert session_data["context"] == context
    
    def test_create_session_empty_record_id(self, session_storage):
        """Test session creation with empty record_id"""
        with pytest.raises(SessionStorageError):
            session_storage.create_session("", {"test": "data"})
    
    def test_create_session_empty_context(self, session_storage):
        """Test session creation with empty context"""
        with pytest.raises(SessionStorageError):
            session_storage.create_session("001XXXX", {})
    
    def test_get_session_success(self, session_storage):
        """Test successful session retrieval"""
        record_id = "001XXXX"
        context = {"test": "data"}
        
        session_id = session_storage.create_session(record_id, context)
        result = session_storage.get_session(session_id)
        
        assert result is not None
        assert result["session_id"] == session_id
        assert result["record_id"] == record_id
        assert result["context"] == context
    
    def test_get_session_not_found(self, session_storage):
        """Test session retrieval when not found"""
        result = session_storage.get_session("non-existent-session-id")
        assert result is None
    
    def test_get_session_empty_id(self, session_storage):
        """Test session retrieval with empty ID"""
        result = session_storage.get_session("")
        assert result is None
    
    def test_get_session_expired(self, session_storage):
        """Test session retrieval when expired"""
        record_id = "001XXXX"
        context = {"test": "data"}
        
        # Create session with very short TTL
        session_id = session_storage.create_session(record_id, context)
        
        # Manually expire the session by updating expires_at
        import sqlite3
        with sqlite3.connect(session_storage.db_path) as conn:
            conn.execute(
                "UPDATE sessions SET expires_at = ? WHERE session_id = ?",
                ((datetime.utcnow() - timedelta(seconds=1)).isoformat(), session_id)
            )
            conn.commit()
        
        # Should return None for expired session
        result = session_storage.get_session(session_id)
        assert result is None
    
    def test_update_session_success(self, session_storage):
        """Test successful session update"""
        record_id = "001XXXX"
        context = {"test": "data"}
        
        session_id = session_storage.create_session(record_id, context)
        
        updates = {"context": {"new": "value", "test": "data"}}
        result = session_storage.update_session(session_id, updates)
        
        assert result is True
        
        # Verify update
        session_data = session_storage.get_session(session_id)
        assert session_data["context"]["new"] == "value"
    
    def test_update_session_not_found(self, session_storage):
        """Test session update when not found"""
        result = session_storage.update_session("non-existent", {"test": "data"})
        assert result is False
    
    def test_update_session_empty_id(self, session_storage):
        """Test session update with empty ID"""
        result = session_storage.update_session("", {"test": "data"})
        assert result is False
    
    def test_delete_session_success(self, session_storage):
        """Test successful session deletion"""
        record_id = "001XXXX"
        context = {"test": "data"}
        
        session_id = session_storage.create_session(record_id, context)
        result = session_storage.delete_session(session_id)
        
        assert result is True
        
        # Verify deletion
        session_data = session_storage.get_session(session_id)
        assert session_data is None
    
    def test_delete_session_not_found(self, session_storage):
        """Test session deletion when not found"""
        result = session_storage.delete_session("non-existent")
        assert result is False
    
    def test_delete_session_empty_id(self, session_storage):
        """Test session deletion with empty ID"""
        result = session_storage.delete_session("")
        assert result is False
    
    def test_extend_session_ttl_success(self, session_storage):
        """Test successful TTL extension"""
        record_id = "001XXXX"
        context = {"test": "data"}
        
        session_id = session_storage.create_session(record_id, context)
        
        # Get original expires_at
        original_data = session_storage.get_session(session_id)
        original_expires = datetime.fromisoformat(original_data["expires_at"])
        
        # Extend TTL
        result = session_storage.extend_session_ttl(session_id, ttl=7200)
        assert result is True
        
        # Verify TTL was extended
        updated_data = session_storage.get_session(session_id)
        updated_expires = datetime.fromisoformat(updated_data["expires_at"])
        assert updated_expires > original_expires
    
    def test_extend_session_ttl_not_found(self, session_storage):
        """Test TTL extension when session not found"""
        result = session_storage.extend_session_ttl("non-existent")
        assert result is False
    
    def test_extend_session_ttl_default(self, session_storage):
        """Test TTL extension with default TTL"""
        record_id = "001XXXX"
        context = {"test": "data"}
        
        session_id = session_storage.create_session(record_id, context)
        
        # Get original expires_at
        original_data = session_storage.get_session(session_id)
        original_expires = datetime.fromisoformat(original_data["expires_at"])
        
        # Extend with default TTL (3600 seconds)
        result = session_storage.extend_session_ttl(session_id)
        assert result is True
        
        # Verify TTL was extended
        updated_data = session_storage.get_session(session_id)
        updated_expires = datetime.fromisoformat(updated_data["expires_at"])
        assert updated_expires > original_expires
    
    def test_cleanup_expired_sessions(self, session_storage):
        """Test automatic cleanup of expired sessions"""
        record_id = "001XXXX"
        context = {"test": "data"}
        
        # Create a session
        session_id = session_storage.create_session(record_id, context)
        
        # Manually expire it
        import sqlite3
        with sqlite3.connect(session_storage.db_path) as conn:
            conn.execute(
                "UPDATE sessions SET expires_at = ? WHERE session_id = ?",
                ((datetime.utcnow() - timedelta(seconds=1)).isoformat(), session_id)
            )
            conn.commit()
        
        # Call get_session which should trigger cleanup
        result = session_storage.get_session(session_id)
        assert result is None
        
        # Verify session was deleted from database
        with sqlite3.connect(session_storage.db_path) as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM sessions WHERE session_id = ?",
                (session_id,)
            )
            count = cursor.fetchone()[0]
            assert count == 0
    
    def test_multiple_sessions(self, session_storage):
        """Test creating and retrieving multiple sessions"""
        sessions = []
        for i in range(5):
            record_id = f"001XXXX{i}"
            context = {"index": i}
            session_id = session_storage.create_session(record_id, context)
            sessions.append((session_id, record_id, context))
        
        # Verify all sessions can be retrieved
        for session_id, record_id, context in sessions:
            data = session_storage.get_session(session_id)
            assert data is not None
            assert data["record_id"] == record_id
            assert data["context"] == context
