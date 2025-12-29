"""Configuration management"""
from pydantic_settings import BaseSettings
from typing import Optional
import os
from dotenv import load_dotenv

# Load .env file explicitly
load_dotenv(override=True)


class LimitsConfig(BaseSettings):
    """Configuration for size limits and truncation"""
    
    # Text blocks limits
    max_text_blocks: int = 50
    max_text_block_length: int = 200
    
    # OCR text limits
    max_ocr_text_length: int = 5000
    
    # Prompt limits
    max_prompt_length: int = 4000
    
    # Pagination settings
    text_blocks_batch_size: int = 50
    ocr_text_chunk_size: int = 4000
    ocr_text_chunk_overlap: int = 200  # Overlap for context preservation
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        env_prefix = "LIMITS_"


class Settings(BaseSettings):
    """Application settings"""
    
    # Application
    app_name: str = "Backend LangGraph Service"
    debug: bool = False
    log_level: str = "DEBUG"
    
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
limits_config = LimitsConfig()

# Debug: Log mock_mode value at startup
import logging
logger = logging.getLogger(__name__)
logger.info(f"Settings loaded: mock_mode={settings.mock_mode} (type: {type(settings.mock_mode).__name__})")
logger.info(f"Environment MOCK_MODE: {os.getenv('MOCK_MODE', 'not set')}")
logger.info(f"Limits config: max_text_blocks={limits_config.max_text_blocks}, max_ocr_text_length={limits_config.max_ocr_text_length}")

