"""Configuration management"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv(override=True)


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Backend LangGraph Service"
    debug: bool = False
    log_level: str = "INFO"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8002
    
    # Mock mode (for testing without LLM API)
    # Pydantic will convert string "true"/"True"/"1" to bool True
    mock_mode: bool = False
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


settings = Settings()

# Debug: Log mock_mode value at startup
import logging
logger = logging.getLogger(__name__)
logger.info(f"Settings loaded: mock_mode={settings.mock_mode} (type: {type(settings.mock_mode).__name__})")
logger.info(f"Environment MOCK_MODE: {os.getenv('MOCK_MODE', 'not set')}")

