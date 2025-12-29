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
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

