"""Custom exceptions"""


class MCPError(Exception):
    """Base exception for MCP service"""
    pass


class SalesforceClientError(MCPError):
    """Error in Salesforce client"""
    pass


class SessionNotFoundError(MCPError):
    """Session not found"""
    pass


class InvalidRequestError(MCPError):
    """Invalid request parameters"""
    pass


class SessionStorageError(MCPError):
    """Error in session storage"""
    pass


class SessionExpiredError(MCPError):
    """Session expired"""
    pass


class WorkflowError(MCPError):
    """Error in workflow execution"""
    pass