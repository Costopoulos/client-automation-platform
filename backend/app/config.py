import os
from pathlib import Path
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with validation"""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Source directories
    base_dir: str = "dummy_data"

    @property
    def forms_dir(self) -> str:
        """Path to forms directory"""
        return os.path.join(self.base_dir, "forms")

    @property
    def emails_dir(self) -> str:
        """Path to emails directory"""
        return os.path.join(self.base_dir, "emails")

    @property
    def invoices_dir(self) -> str:
        """Path to invoices directory"""
        return os.path.join(self.base_dir, "invoices")

    # OpenAI Configuration
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_temperature: float = 0.1
    openai_timeout: int = 30

    # Google Sheets Configuration
    google_credentials_path: str = "credentials/service-account.json"
    google_spreadsheet_id: str

    # Logging
    log_level: str = "INFO"
    log_file: str = "logs/automation.log"

    # API Configuration
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        """Parse CORS origins into a list"""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @field_validator("openai_api_key")
    @classmethod
    def validate_openai_api_key(cls, v: str) -> str:
        """Validate OpenAI API key is present"""
        if not v or v.startswith("sk-your-"):
            raise ValueError(
                "OPENAI_API_KEY must be set to a valid API key. "
                "Please update your .env file with a real API key."
            )
        return v

    @field_validator("google_credentials_path")
    @classmethod
    def validate_google_credentials(cls, v: str) -> str:
        """Validate Google credentials path is provided"""
        # Don't check file existence here - it will be checked at runtime
        # This allows for more flexible testing
        return v

    @field_validator("google_spreadsheet_id")
    @classmethod
    def validate_spreadsheet_id(cls, v: str) -> str:
        """Validate Google Spreadsheet ID is present"""
        if not v or v.startswith("your-spreadsheet-id"):
            raise ValueError(
                "GOOGLE_SPREADSHEET_ID must be set to a valid spreadsheet ID. "
                "Please update your .env file with a real spreadsheet ID."
            )
        return v

    @field_validator("base_dir")
    @classmethod
    def validate_base_dir(cls, v: str) -> str:
        """Validate base directory exists"""
        path = Path(v)
        if not path.exists():
            raise ValueError(
                f"Base directory '{v}' does not exist. "
                f"Please ensure the directory exists or update BASE_DIR in .env"
            )
        return v

    def validate_source_directories(self) -> None:
        """Validate that all source directories exist"""
        directories = {
            "forms": self.forms_dir,
            "emails": self.emails_dir,
            "invoices": self.invoices_dir,
        }

        missing = []
        for name, path in directories.items():
            if not Path(path).exists():
                missing.append(f"{name} ({path})")

        if missing:
            raise ValueError(
                f"Missing source directories: {', '.join(missing)}. "
                f"Please ensure these directories exist under {self.base_dir}"
            )

    def ensure_log_directory(self) -> None:
        """Ensure log directory exists"""
        log_path = Path(self.log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)


# Global settings instance
settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create settings instance"""
    global settings
    if settings is None:
        settings = Settings()
        settings.validate_source_directories()
        settings.ensure_log_directory()
    return settings
