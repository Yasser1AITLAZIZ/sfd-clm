"""Configuration management"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Backend MCP Service"
    debug: bool = False
    log_level: str = "DEBUG"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # External services
    mock_salesforce_url: str = "http://localhost:8001"
    salesforce_request_timeout: float = 5.0
    
    # Session storage configuration (SQLite)
    # Can be overridden by SESSION_DB_PATH environment variable
    session_db_path: str = "data/sessions.db"
    session_ttl_seconds: int = 86400  # 24 hours
    
    # Document uploads configuration
    uploads_dir: str = "uploads"
    
    # Langgraph configuration
    langgraph_url: str = "http://localhost:8002"
    langgraph_api_key: Optional[str] = None
    langgraph_timeout: float = 175.0  # Increased from 120.0 to 150-200s range
    
    # Adaptive timeout configuration
    timeout_base: float = 50.0  # Base timeout in seconds (increased from 30.0 for more headroom)
    timeout_per_field: float = 0.5  # Additional seconds per field
    timeout_per_document: float = 10.0  # Additional seconds per document
    timeout_max: float = 300.0  # Maximum timeout (5 minutes)
    
    # Per-step timeouts
    preprocessing_timeout: float = 10.0
    ocr_timeout_per_page: float = 60.0
    llm_extraction_timeout: float = 120.0
    validation_timeout: float = 30.0
    
    # Celery configuration (for async tasks - not currently used)
    # TODO: Celery is planned for future async task processing
    # celery_broker_url: str = "redis://localhost:6379/1"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

