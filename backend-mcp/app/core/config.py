"""Configuration management"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Backend MCP Service"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # External services
    mock_salesforce_url: str = "http://localhost:8001"
    salesforce_request_timeout: float = 5.0
    
    # Session storage configuration (SQLite)
    session_db_path: str = "data/sessions.db"
    session_ttl_seconds: int = 86400  # 24 hours
    
    # Langgraph configuration
    langgraph_url: str = "http://localhost:8002"
    langgraph_api_key: Optional[str] = None
    langgraph_timeout: float = 30.0
    
    # Celery configuration (for async tasks - not currently used)
    # TODO: Celery is planned for future async task processing
    # celery_broker_url: str = "redis://localhost:6379/1"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

