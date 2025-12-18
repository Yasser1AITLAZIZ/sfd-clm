"""Tests for SessionManager"""
import pytest
import sys
from pathlib import Path
import os
from unittest.mock import Mock, MagicMock, patch
from datetime import datetime

# Setup path for imports
project_root = Path(__file__).parent.parent
mcp_path = project_root / "backend-mcp"
original_cwd = os.getcwd()
try:
    os.chdir(mcp_path)
    sys.path.insert(0, str(mcp_path))
    from app.services.session_manager import SessionManager
    from app.services.session_storage import SessionStorage
    from app.models.schemas import (
        SalesforceDataResponseSchema,
        DocumentResponseSchema,
        FieldToFillResponseSchema
    )
    from app.core.exceptions import (
        SessionStorageError,
        SessionNotFoundError,
        InvalidRequestError
    )
finally:
    os.chdir(original_cwd)
    if str(mcp_path) in sys.path:
        sys.path.remove(str(mcp_path))


class TestSessionManager:
    """Test cases for SessionManager"""
    
    @pytest.fixture
    def mock_storage(self):
        """Mock SessionStorage"""
        return MagicMock(spec=SessionStorage)
    
    @pytest.fixture
    def session_manager(self, mock_storage):
        """Create SessionManager instance with mocked storage"""
        return SessionManager(mock_storage)
    
    @pytest.fixture
    def sample_salesforce_data(self):
        """Sample Salesforce data for testing"""
        return SalesforceDataResponseSchema(
            record_id="001XXXX",
            record_type="Claim",
            documents=[
                DocumentResponseSchema(
                    document_id="doc_1",
                    name="facture.pdf",
                    url="https://example.com/facture.pdf",
                    type="application/pdf",
                    indexed=True
                )
            ],
            fields_to_fill=[
                FieldToFillResponseSchema(
                    field_name="montant_total",
                    field_type="currency",
                    value=None,
                    required=True,
                    label="Montant total"
                )
            ]
        )
    
    def test_init(self, mock_storage):
        """Test SessionManager initialization"""
        manager = SessionManager(mock_storage)
        assert manager.storage == mock_storage
    
    def test_initialize_session_success(self, session_manager, mock_storage, sample_salesforce_data):
        """Test successful session initialization"""
        session_id = "test-session-id"
        mock_storage.create_session.return_value = session_id
        
        result = session_manager.initialize_session("001XXXX", sample_salesforce_data)
        
        assert result == session_id
        mock_storage.create_session.assert_called_once()
        
        # Verify context structure
        call_args = mock_storage.create_session.call_args
        assert call_args[0][0] == "001XXXX"  # record_id
        context = call_args[0][1]  # context
        assert "salesforce_data" in context
        assert "conversation_history" in context
        assert context["conversation_history"] == []
        assert "extracted_data" in context
        assert context["extracted_data"] == {}
        assert "metadata" in context
        assert context["metadata"]["preprocessing_completed"] is False
    
    def test_initialize_session_empty_record_id(self, session_manager, sample_salesforce_data):
        """Test initialization with empty record_id"""
        with pytest.raises(InvalidRequestError):
            session_manager.initialize_session("", sample_salesforce_data)
    
    def test_initialize_session_empty_data(self, session_manager):
        """Test initialization with empty salesforce_data"""
        with pytest.raises(InvalidRequestError):
            session_manager.initialize_session("001XXXX", None)
    
    def test_initialize_session_storage_error(self, session_manager, mock_storage, sample_salesforce_data):
        """Test initialization with storage error"""
        mock_storage.create_session.side_effect = SessionStorageError("Storage error")
        with pytest.raises(SessionStorageError):
            session_manager.initialize_session("001XXXX", sample_salesforce_data)
    
    def test_check_session_exists_true(self, session_manager, mock_storage):
        """Test checking existing session"""
        session_id = "test-session-id"
        mock_storage.get_session.return_value = {"session_id": session_id}
        
        result = session_manager.check_session_exists(session_id)
        
        assert result is True
        mock_storage.get_session.assert_called_once_with(session_id)
    
    def test_check_session_exists_false(self, session_manager, mock_storage):
        """Test checking non-existent session"""
        mock_storage.get_session.return_value = None
        
        result = session_manager.check_session_exists("non-existent")
        
        assert result is False
    
    def test_check_session_exists_empty_id(self, session_manager):
        """Test checking session with empty ID"""
        result = session_manager.check_session_exists("")
        assert result is False
    
    def test_append_message_to_history_success(self, session_manager, mock_storage):
        """Test successful message append"""
        session_id = "test-session-id"
        existing_session = {
            "session_id": session_id,
            "record_id": "001XXXX",
            "context": {
                "conversation_history": [],
                "salesforce_data": {},
                "extracted_data": {},
                "metadata": {}
            }
        }
        mock_storage.get_session.return_value = existing_session
        mock_storage.update_session.return_value = True
        
        result = session_manager.append_message_to_history(session_id, "user", "Hello")
        
        assert result is True
        mock_storage.update_session.assert_called_once()
        
        # Verify message was added
        call_args = mock_storage.update_session.call_args
        updates = call_args[0][1]
        assert "context" in updates
        history = updates["context"]["conversation_history"]
        assert len(history) == 1
        assert history[0]["role"] == "user"
        assert history[0]["message"] == "Hello"
        assert "timestamp" in history[0]
    
    def test_append_message_to_history_invalid_role(self, session_manager):
        """Test appending message with invalid role"""
        with pytest.raises(InvalidRequestError):
            session_manager.append_message_to_history("test-id", "invalid", "Hello")
    
    def test_append_message_to_history_empty_message(self, session_manager):
        """Test appending empty message"""
        with pytest.raises(InvalidRequestError):
            session_manager.append_message_to_history("test-id", "user", "")
    
    def test_append_message_to_history_session_not_found(self, session_manager, mock_storage):
        """Test appending message to non-existent session"""
        mock_storage.get_session.return_value = None
        
        result = session_manager.append_message_to_history("non-existent", "user", "Hello")
        
        assert result is False
    
    def test_get_session_context_success(self, session_manager, mock_storage):
        """Test successful context retrieval"""
        session_id = "test-session-id"
        context = {
            "salesforce_data": {"record_id": "001XXXX"},
            "conversation_history": [],
            "extracted_data": {},
            "metadata": {}
        }
        existing_session = {
            "session_id": session_id,
            "record_id": "001XXXX",
            "context": context
        }
        mock_storage.get_session.return_value = existing_session
        
        result = session_manager.get_session_context(session_id)
        
        assert result == context
        mock_storage.get_session.assert_called_once_with(session_id)
    
    def test_get_session_context_not_found(self, session_manager, mock_storage):
        """Test context retrieval for non-existent session"""
        mock_storage.get_session.return_value = None
        
        result = session_manager.get_session_context("non-existent")
        
        assert result is None
    
    def test_get_session_context_no_context(self, session_manager, mock_storage):
        """Test context retrieval when session has no context"""
        existing_session = {
            "session_id": "test-id",
            "record_id": "001XXXX"
        }
        mock_storage.get_session.return_value = existing_session
        
        result = session_manager.get_session_context("test-id")
        
        assert result is None
    
    def test_extend_session_ttl_success(self, session_manager, mock_storage):
        """Test successful TTL extension"""
        session_id = "test-session-id"
        mock_storage.extend_session_ttl.return_value = True
        
        result = session_manager.extend_session_ttl(session_id, ttl=7200)
        
        assert result is True
        mock_storage.extend_session_ttl.assert_called_once_with(session_id, 7200)
    
    def test_extend_session_ttl_default(self, session_manager, mock_storage):
        """Test TTL extension with default TTL"""
        session_id = "test-session-id"
        mock_storage.extend_session_ttl.return_value = True
        
        result = session_manager.extend_session_ttl(session_id)
        
        assert result is True
        mock_storage.extend_session_ttl.assert_called_once_with(session_id, None)
    
    def test_extend_session_ttl_not_found(self, session_manager, mock_storage):
        """Test TTL extension for non-existent session"""
        mock_storage.extend_session_ttl.return_value = False
        
        result = session_manager.extend_session_ttl("non-existent")
        
        assert result is False

