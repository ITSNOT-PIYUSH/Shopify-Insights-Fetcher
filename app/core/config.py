"""
Configuration settings for the Shopify Insights Fetcher application.
"""
import os
from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings with environment variable support."""
    
    # Application settings
    app_name: str = "Shopify Insights Fetcher"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, description="Enable debug mode")
    
    # API settings
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, description="API port")
    
    # Database settings (MySQL)
    database_url: Optional[str] = Field(
        default=None,
        description="Database URL for MySQL connection"
    )
    db_host: str = Field(default="localhost", description="Database host")
    db_port: int = Field(default=3306, description="Database port")
    db_name: str = Field(default="shopify_insights", description="Database name")
    db_user: str = Field(default="root", description="Database user")
    db_password: str = Field(default="", description="Database password")
    
    # External API settings
    openai_api_key: Optional[str] = Field(
        default=None,
        description="OpenAI API key for text processing"
    )
    
    # Scraping settings
    request_timeout: int = Field(default=30, description="HTTP request timeout in seconds")
    max_retries: int = Field(default=3, description="Maximum number of retry attempts")
    user_agent: str = Field(
        default="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        description="User agent for HTTP requests"
    )
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow"
    }

    @property
    def mysql_url(self) -> str:
        """Construct MySQL database URL."""
        if self.database_url:
            return self.database_url
        
        return f"mysql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"


# Global settings instance
settings = Settings()
