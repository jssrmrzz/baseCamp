"""Configuration settings for baseCamp application."""

from typing import List, Literal, Optional
from pydantic import BaseSettings, Field, validator
import os


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Configuration
    api_host: str = Field(default="0.0.0.0", env="API_HOST")
    api_port: int = Field(default=8000, env="API_PORT")
    debug: bool = Field(default=False, env="DEBUG")
    api_secret_key: str = Field(
        default="dev-secret-key-change-in-production", 
        env="API_SECRET_KEY"
    )

    # LLM Configuration (Ollama)
    ollama_base_url: str = Field(default="http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="mistral:latest", env="OLLAMA_MODEL")
    ollama_timeout: int = Field(default=30, env="OLLAMA_TIMEOUT")

    # Vector Database Configuration (ChromaDB)
    chroma_persist_directory: str = Field(default="./chroma_db", env="CHROMA_PERSIST_DIRECTORY")
    chroma_collection_name: str = Field(default="leads", env="CHROMA_COLLECTION_NAME")

    # Airtable CRM Integration
    airtable_api_key: Optional[str] = Field(default=None, env="AIRTABLE_API_KEY")
    airtable_base_id: Optional[str] = Field(default=None, env="AIRTABLE_BASE_ID")
    airtable_table_name: str = Field(default="Leads", env="AIRTABLE_TABLE_NAME")

    # Lead Processing Configuration
    lead_similarity_threshold: float = Field(default=0.85, env="LEAD_SIMILARITY_THRESHOLD")
    max_similar_leads: int = Field(default=5, env="MAX_SIMILAR_LEADS")
    business_type: Literal["automotive", "medspa", "consulting", "general"] = Field(
        default="general", env="BUSINESS_TYPE"
    )

    # Rate Limiting
    rate_limit_requests_per_minute: int = Field(default=60, env="RATE_LIMIT_REQUESTS_PER_MINUTE")
    rate_limit_requests_per_hour: int = Field(default=1000, env="RATE_LIMIT_REQUESTS_PER_HOUR")

    # Logging Configuration
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = Field(
        default="INFO", env="LOG_LEVEL"
    )
    log_format: Literal["json", "text"] = Field(default="json", env="LOG_FORMAT")

    # Security Settings
    cors_origins: List[str] = Field(
        default=["http://localhost:3000"], env="CORS_ORIGINS"
    )
    allowed_hosts: List[str] = Field(
        default=["localhost", "127.0.0.1"], env="ALLOWED_HOSTS"
    )

    # Background Processing
    enable_background_tasks: bool = Field(default=True, env="ENABLE_BACKGROUND_TASKS")
    background_task_timeout: int = Field(default=300, env="BACKGROUND_TASK_TIMEOUT")

    # Development Settings
    reload_on_change: bool = Field(default=False, env="RELOAD_ON_CHANGE")
    enable_api_docs: bool = Field(default=True, env="ENABLE_API_DOCS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            # Handle both JSON-like strings and comma-separated strings
            if v.startswith("[") and v.endswith("]"):
                # Remove brackets and split by comma
                v = v[1:-1].replace('"', '').replace("'", "")
                return [origin.strip() for origin in v.split(",") if origin.strip()]
            else:
                return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @validator("allowed_hosts", pre=True)
    def parse_allowed_hosts(cls, v):
        """Parse allowed hosts from string or list."""
        if isinstance(v, str):
            return [host.strip() for host in v.split(",") if host.strip()]
        return v

    @validator("chroma_persist_directory")
    def validate_chroma_directory(cls, v):
        """Ensure ChromaDB directory exists."""
        if not os.path.exists(v):
            os.makedirs(v, exist_ok=True)
        return v

    @validator("lead_similarity_threshold")
    def validate_similarity_threshold(cls, v):
        """Ensure similarity threshold is between 0 and 1."""
        if not 0.0 <= v <= 1.0:
            raise ValueError("similarity_threshold must be between 0.0 and 1.0")
        return v

    @validator("airtable_api_key")
    def validate_airtable_config(cls, v, values):
        """Validate Airtable configuration if provided."""
        if v and not values.get("airtable_base_id"):
            raise ValueError("airtable_base_id is required when airtable_api_key is provided")
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.debug or self.reload_on_change

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return not self.is_development

    @property
    def airtable_configured(self) -> bool:
        """Check if Airtable integration is configured."""
        return bool(self.airtable_api_key and self.airtable_base_id)

    def get_docs_url(self) -> Optional[str]:
        """Get API documentation URL if enabled."""
        return "/docs" if self.enable_api_docs else None

    def get_redoc_url(self) -> Optional[str]:
        """Get ReDoc documentation URL if enabled."""
        return "/redoc" if self.enable_api_docs else None


# Global settings instance
settings = Settings()