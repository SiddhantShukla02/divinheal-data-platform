# -----------------------------------------------------------------------------
# SETTINGS TESTS
# -----------------------------------------------------------------------------
# PURPOSE:
#   Verifies that application settings load correctly from environment variables.
#
# INPUT:
#   load_settings() and AppSettings from divinheal_data.core.settings.
#
# PROCESS:
#   - Clears relevant environment variables for default-value tests.
#   - Sets environment variables for override tests.
#   - Confirms blank optional R2 values are treated as missing.
#
# OUTPUT:
#   Passing tests for settings defaults, overrides, and optional env handling.
#
# NOTES:
#   - These tests do not connect to Postgres or R2.
#   - They only validate config-loading behavior.
# -----------------------------------------------------------------------------

import pytest

from divinheal_data.core.settings import load_settings


def test_load_settings_uses_local_defaults(monkeypatch) -> None:
    env_names = [
        "APP_ENV",
        "STORAGE_BACKEND",
        "LOCAL_DATA_DIR",
        "DATABASE_URL",
        "HTTP_TIMEOUT_SECONDS",
        "HTTP_MAX_RETRIES",
        "R2_ACCOUNT_ID",
        "R2_ACCESS_KEY_ID",
        "R2_SECRET_ACCESS_KEY",
        "R2_BUCKET_NAME",
        "R2_ENDPOINT_URL",
        "ENABLE_AI_OUTBOUND_ESTIMATES",
        "AI_OUTBOUND_ESTIMATE_MAX_ORIGINS",
        "AI_OUTBOUND_ESTIMATE_REFRESH_CACHE",
        "GEMINI_API_KEY",
    ]

    for name in env_names:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("ENABLE_AI_OUTBOUND_ESTIMATES", "false")
    monkeypatch.setenv("AI_OUTBOUND_ESTIMATE_MAX_ORIGINS", "8")
    monkeypatch.setenv("AI_OUTBOUND_ESTIMATE_REFRESH_CACHE", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    
    settings = load_settings()

    assert settings.app_env == "local"
    assert settings.storage_backend == "local"
    assert settings.local_data_dir == "data"
    assert (
        settings.database_url
        == "postgresql://divinheal:divinheal_dev_password@localhost:5433/divinheal_data"
    )
    assert settings.http_timeout_seconds == 30
    assert settings.http_max_retries == 3
    assert settings.enable_ai_outbound_estimates is False
    assert settings.ai_outbound_estimate_max_origins == 8
    assert settings.ai_outbound_estimate_refresh_cache is False
    assert settings.gemini_api_key is None
    assert settings.r2_account_id is None
    assert settings.r2_access_key_id is None
    assert settings.r2_secret_access_key is None
    assert settings.r2_bucket_name is None
    assert settings.r2_endpoint_url is None


def test_load_settings_uses_environment_overrides(monkeypatch) -> None:
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("STORAGE_BACKEND", "local")
    monkeypatch.setenv("LOCAL_DATA_DIR", "tmp_data")
    monkeypatch.setenv("DATABASE_URL", "postgresql://user:pass@localhost:5432/test_db")
    monkeypatch.setenv("HTTP_TIMEOUT_SECONDS", "10")
    monkeypatch.setenv("HTTP_MAX_RETRIES", "1")
    monkeypatch.setenv("R2_ACCOUNT_ID", "account")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "access")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("R2_BUCKET_NAME", "bucket")
    monkeypatch.setenv("R2_ENDPOINT_URL", "https://example.r2.cloudflarestorage.com")
    monkeypatch.setenv("ENABLE_AI_OUTBOUND_ESTIMATES", "true")
    monkeypatch.setenv("AI_OUTBOUND_ESTIMATE_MAX_ORIGINS", "5")
    monkeypatch.setenv("AI_OUTBOUND_ESTIMATE_REFRESH_CACHE", "yes")
    monkeypatch.setenv("GEMINI_API_KEY", "fake-test-key")

    settings = load_settings()

    assert settings.app_env == "test"
    assert settings.storage_backend == "local"
    assert settings.local_data_dir == "tmp_data"
    assert settings.database_url == "postgresql://user:pass@localhost:5432/test_db"
    assert settings.http_timeout_seconds == 10
    assert settings.http_max_retries == 1
    assert settings.enable_ai_outbound_estimates is True
    assert settings.ai_outbound_estimate_max_origins == 5
    assert settings.ai_outbound_estimate_refresh_cache is True
    assert settings.gemini_api_key == "fake-test-key"
    assert settings.r2_account_id == "account"
    assert settings.r2_access_key_id == "access"
    assert settings.r2_secret_access_key == "secret"
    assert settings.r2_bucket_name == "bucket"
    assert settings.r2_endpoint_url == "https://example.r2.cloudflarestorage.com"


def test_blank_optional_r2_values_are_treated_as_missing(monkeypatch) -> None:
    monkeypatch.setenv("R2_ACCOUNT_ID", "")
    monkeypatch.setenv("R2_ACCESS_KEY_ID", "")
    monkeypatch.setenv("R2_SECRET_ACCESS_KEY", "")
    monkeypatch.setenv("R2_BUCKET_NAME", "")
    monkeypatch.setenv("R2_ENDPOINT_URL", "")

    settings = load_settings()

    assert settings.r2_account_id is None
    assert settings.r2_access_key_id is None
    assert settings.r2_secret_access_key is None
    assert settings.r2_bucket_name is None
    assert settings.r2_endpoint_url is None

def test_load_settings_rejects_invalid_boolean_env(monkeypatch) -> None:
    monkeypatch.setenv("ENABLE_AI_OUTBOUND_ESTIMATES", "maybe")

    with pytest.raises(ValueError, match="ENABLE_AI_OUTBOUND_ESTIMATES must be a boolean"):
        load_settings()