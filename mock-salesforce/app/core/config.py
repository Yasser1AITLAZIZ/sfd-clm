"""Configuration management"""
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Mock Salesforce Service"
    debug: bool = False
    log_level: str = "DEBUG"
    
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    
    # File server configuration
    file_server_url: str = "http://localhost:8001"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

