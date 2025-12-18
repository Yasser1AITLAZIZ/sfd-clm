"""Custom exceptions"""


class MockSalesforceError(Exception):
    """Base exception for Mock Salesforce service"""
    pass


class RecordNotFoundError(MockSalesforceError):
    """Record not found in mock data"""
    pass


class InvalidRecordIdError(MockSalesforceError):
    """Invalid record ID format"""
    pass

