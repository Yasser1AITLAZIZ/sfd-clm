"""Pytest configuration and fixtures"""
import pytest
from httpx import AsyncClient, ASGITransport
from fastapi import FastAPI
import sys
from pathlib import Path
import os

project_root = Path(__file__).parent.parent
mock_path = project_root / "mock-salesforce"
mcp_path = project_root / "backend-mcp"

# Import mock app
original_cwd = os.getcwd()
try:
    os.chdir(mock_path)
    sys.path.insert(0, str(mock_path))
    from app.main import app as mock_app
finally:
    os.chdir(original_cwd)

# Import MCP app
try:
    os.chdir(mcp_path)
    sys.path.insert(0, str(mcp_path))
    from app.main import app as mcp_app
finally:
    os.chdir(original_cwd)


@pytest.fixture
async def mock_client():
    """Async client for mock Salesforce service"""
    async with AsyncClient(transport=ASGITransport(app=mock_app), base_url="http://test") as client:
        yield client


@pytest.fixture
async def mcp_client():
    """Async client for backend MCP service"""
    async with AsyncClient(transport=ASGITransport(app=mcp_app), base_url="http://test") as client:
        yield client

