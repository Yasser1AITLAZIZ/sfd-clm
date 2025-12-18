"""Tests for SessionStorage"""
import pytest
import json
import sys
from pathlib import Path
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
import redis
from redis.exceptions import ConnectionError, TimeoutError, RedisError

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
    def mock_redis(self):
        """Mock Redis client"""
        with patch('backend_mcp.app.services.session_storage.redis.from_url') as mock_from_url:
            mock_client = MagicMock()
            mock_client.ping.return_value = True
            mock_from_url.return_value = mock_client
            yield mock_client
    
    @pytest.fixture
    def session_storage(self, mock_redis):
        """Create SessionStorage instance with mocked Redis"""
        return SessionStorage("redis://localhost:6379/0", default_ttl=3600)
    
    def test_init_success(self, mock_redis):
        """Test successful initialization"""
        storage = SessionStorage("redis://localhost:6379/0", default_ttl=3600)
        assert storage.default_ttl == 3600
        assert storage.key_prefix == "session:"
        mock_redis.ping.assert_called_once()
    
    def test_init_connection_error(self):
        """Test initialization with connection error"""
        with patch('backend_mcp.app.services.session_storage.redis.from_url') as mock_from_url:
            mock_from_url.side_effect = ConnectionError("Connection failed")
            with pytest.raises(SessionStorageError):
                SessionStorage("redis://localhost:6379/0")
    
    def test_create_session_success(self, session_storage, mock_redis):
        """Test successful session creation"""
        record_id = "001XXXX"
        context = {"test": "data"}
        
        session_id = session_storage.create_session(record_id, context)
        
        assert session_id is not None
        assert len(session_id) == 36  # UUID v4 length
        mock_redis.setex.assert_called_once()
        
        # Verify call arguments
        call_args = mock_redis.setex.call_args
        assert call_args[0][0].startswith("session:")
        assert call_args[0][1] == 3600  # TTL
        session_data = json.loads(call_args[0][2])
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
    
    def test_create_session_redis_error(self, session_storage, mock_redis):
        """Test session creation with Redis error"""
        mock_redis.setex.side_effect = ConnectionError("Connection failed")
        with pytest.raises(SessionStorageError):
            session_storage.create_session("001XXXX", {"test": "data"})
    
    def test_get_session_success(self, session_storage, mock_redis):
        """Test successful session retrieval"""
        session_id = "test-session-id"
        session_data = {
            "session_id": session_id,
            "record_id": "001XXXX",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "context": {"test": "data"}
        }
        mock_redis.get.return_value = json.dumps(session_data)
        
        result = session_storage.get_session(session_id)
        
        assert result is not None
        assert result["session_id"] == session_id
        assert result["record_id"] == "001XXXX"
        mock_redis.get.assert_called_once_with("session:test-session-id")
    
    def test_get_session_not_found(self, session_storage, mock_redis):
        """Test session retrieval when not found"""
        mock_redis.get.return_value = None
        
        result = session_storage.get_session("non-existent")
        
        assert result is None
    
    def test_get_session_empty_id(self, session_storage):
        """Test session retrieval with empty ID"""
        result = session_storage.get_session("")
        assert result is None
    
    def test_get_session_redis_error(self, session_storage, mock_redis):
        """Test session retrieval with Redis error"""
        mock_redis.get.side_effect = ConnectionError("Connection failed")
        result = session_storage.get_session("test-id")
        assert result is None  # Should return None on error
    
    def test_update_session_success(self, session_storage, mock_redis):
        """Test successful session update"""
        session_id = "test-session-id"
        existing_data = {
            "session_id": session_id,
            "record_id": "001XXXX",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "context": {"test": "data"}
        }
        mock_redis.get.return_value = json.dumps(existing_data)
        mock_redis.ttl.return_value = 1800
        
        updates = {"context": {"new": "value"}}
        result = session_storage.update_session(session_id, updates)
        
        assert result is True
        assert mock_redis.setex.called
    
    def test_update_session_not_found(self, session_storage, mock_redis):
        """Test session update when not found"""
        mock_redis.get.return_value = None
        
        result = session_storage.update_session("non-existent", {"test": "data"})
        
        assert result is False
    
    def test_delete_session_success(self, session_storage, mock_redis):
        """Test successful session deletion"""
        session_id = "test-session-id"
        mock_redis.delete.return_value = 1
        
        result = session_storage.delete_session(session_id)
        
        assert result is True
        mock_redis.delete.assert_called_once_with("session:test-session-id")
    
    def test_delete_session_not_found(self, session_storage, mock_redis):
        """Test session deletion when not found"""
        mock_redis.delete.return_value = 0
        
        result = session_storage.delete_session("non-existent")
        
        assert result is False
    
    def test_extend_session_ttl_success(self, session_storage, mock_redis):
        """Test successful TTL extension"""
        session_id = "test-session-id"
        existing_data = {
            "session_id": session_id,
            "record_id": "001XXXX",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "context": {"test": "data"}
        }
        mock_redis.exists.return_value = True
        mock_redis.get.return_value = json.dumps(existing_data)
        
        result = session_storage.extend_session_ttl(session_id, ttl=7200)
        
        assert result is True
        assert mock_redis.setex.called
    
    def test_extend_session_ttl_not_found(self, session_storage, mock_redis):
        """Test TTL extension when session not found"""
        mock_redis.exists.return_value = False
        
        result = session_storage.extend_session_ttl("non-existent")
        
        assert result is False
    
    def test_extend_session_ttl_default(self, session_storage, mock_redis):
        """Test TTL extension with default TTL"""
        session_id = "test-session-id"
        existing_data = {
            "session_id": session_id,
            "record_id": "001XXXX",
            "created_at": datetime.utcnow().isoformat(),
            "updated_at": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=1)).isoformat(),
            "context": {"test": "data"}
        }
        mock_redis.exists.return_value = True
        mock_redis.get.return_value = json.dumps(existing_data)
        
        result = session_storage.extend_session_ttl(session_id)
        
        assert result is True
        # Verify default TTL was used
        call_args = mock_redis.setex.call_args
        assert call_args[0][1] == 3600  # default_ttl

