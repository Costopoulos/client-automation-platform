import os

import pytest

from app.config import Settings


def test_settings_default_values(tmp_path):
    """Test Settings with default values where possible"""
    # Create a temporary credentials file
    creds_file = tmp_path / "test-creds.json"
    creds_file.write_text('{"type":"service_account","project_id":"test"}')

    settings = Settings(
        openai_api_key="sk-test-key-123",
        google_credentials_path=str(creds_file),
        google_spreadsheet_id="test-spreadsheet-id-123",
    )

    assert settings.base_dir == "dummy_data"
    assert settings.openai_model == "gpt-4o-mini"
    assert settings.openai_temperature == 0.1
    assert settings.openai_timeout == 30
    assert settings.log_level == "INFO"
    assert settings.log_file == "logs/automation.log"


def test_settings_directory_properties(tmp_path):
    """Test directory property methods"""
    creds_file = tmp_path / "test-creds.json"
    creds_file.write_text('{"type":"service_account"}')

    settings = Settings(
        base_dir="dummy_data",
        openai_api_key="sk-test-key-123",
        google_credentials_path=str(creds_file),
        google_spreadsheet_id="test-spreadsheet-id-123",
    )

    assert settings.forms_dir == os.path.join("dummy_data", "forms")
    assert settings.emails_dir == os.path.join("dummy_data", "emails")
    assert settings.invoices_dir == os.path.join("dummy_data", "invoices")


def test_settings_cors_origins_list(tmp_path):
    """Test CORS origins parsing"""
    creds_file = tmp_path / "test-creds.json"
    creds_file.write_text('{"type":"service_account"}')

    settings = Settings(
        cors_origins="http://localhost:3000,http://localhost:5173,https://example.com",
        openai_api_key="sk-test-key-123",
        google_credentials_path=str(creds_file),
        google_spreadsheet_id="test-spreadsheet-id-123",
    )

    origins = settings.cors_origins_list
    assert len(origins) == 3
    assert "http://localhost:3000" in origins
    assert "http://localhost:5173" in origins
    assert "https://example.com" in origins


def test_settings_validation_invalid_openai_key(tmp_path):
    """Test validation fails with invalid OpenAI API key"""
    creds_file = tmp_path / "test-creds.json"
    creds_file.write_text('{"type":"service_account"}')

    with pytest.raises(ValueError, match="OPENAI_API_KEY must be set"):
        Settings(
            openai_api_key="sk-your-openai-api-key-here",
            google_credentials_path=str(creds_file),
            google_spreadsheet_id="test-spreadsheet-id-123",
        )


def test_settings_validation_google_credentials_path(tmp_path):
    """Test Google credentials path can be set"""
    creds_file = tmp_path / "test-creds.json"
    creds_file.write_text('{"type":"service_account"}')

    settings = Settings(
        openai_api_key="sk-test-key-123",
        google_credentials_path=str(creds_file),
        google_spreadsheet_id="test-spreadsheet-id-123",
    )

    assert settings.google_credentials_path == str(creds_file)


def test_settings_validation_invalid_spreadsheet_id(tmp_path):
    """Test validation fails with invalid spreadsheet ID"""
    creds_file = tmp_path / "test-creds.json"
    creds_file.write_text('{"type":"service_account"}')

    with pytest.raises(ValueError, match="GOOGLE_SPREADSHEET_ID must be set"):
        Settings(
            openai_api_key="sk-test-key-123",
            google_credentials_path=str(creds_file),
            google_spreadsheet_id="your-spreadsheet-id-here",
        )


def test_settings_validation_nonexistent_base_dir(tmp_path):
    """Test validation fails with nonexistent base directory"""
    creds_file = tmp_path / "test-creds.json"
    creds_file.write_text('{"type":"service_account"}')

    with pytest.raises(ValueError, match="Base directory .* does not exist"):
        Settings(
            base_dir="nonexistent_directory_12345",
            openai_api_key="sk-test-key-123",
            google_credentials_path=str(creds_file),
            google_spreadsheet_id="test-spreadsheet-id-123",
        )


def test_settings_validate_source_directories(tmp_path):
    """Test source directory validation"""
    creds_file = tmp_path / "test-creds.json"
    creds_file.write_text('{"type":"service_account"}')

    settings = Settings(
        base_dir="dummy_data",
        openai_api_key="sk-test-key-123",
        google_credentials_path=str(creds_file),
        google_spreadsheet_id="test-spreadsheet-id-123",
    )

    # This should not raise an error if dummy_data directories exist
    settings.validate_source_directories()


def test_settings_ensure_log_directory(tmp_path):
    """Test log directory creation"""
    creds_file = tmp_path / "test-creds.json"
    creds_file.write_text('{"type":"service_account"}')

    log_file = tmp_path / "logs" / "test.log"

    settings = Settings(
        base_dir="dummy_data",
        log_file=str(log_file),
        openai_api_key="sk-test-key-123",
        google_credentials_path=str(creds_file),
        google_spreadsheet_id="test-spreadsheet-id-123",
    )

    settings.ensure_log_directory()

    assert log_file.parent.exists()
    assert log_file.parent.is_dir()
