# -----------------------------------------------------------------------------
# APPLICATION SETTINGS
# -----------------------------------------------------------------------------
# PURPOSE:
#   Loads runtime configuration from environment variables and .env files.
#
# INPUT:
#   - .env file values
#   - OS environment variables
#
# PROCESS:
#   - Loads .env values using python-dotenv.
#   - Reads known settings with safe local defaults.
#   - Converts numeric settings to integers.
#   - Converts boolean feature flags from strings.
#   - Exposes settings through a typed AppSettings dataclass.
#
# OUTPUT:
#   - AppSettings
#   - load_settings()
#
# NOTES:
#   - This module does not validate external connections.
#   - Secrets should live in .env or OS environment variables, not in code.
# -----------------------------------------------------------------------------

from dataclasses import dataclass
from os import getenv

from dotenv import load_dotenv


@dataclass(frozen=True)
class AppSettings:
    """Runtime settings loaded from environment variables."""

    app_env: str
    storage_backend: str
    local_data_dir: str
    database_url: str
    http_timeout_seconds: int
    http_max_retries: int
    enable_ai_outbound_estimates: bool
    ai_outbound_estimate_max_origins: int
    ai_outbound_estimate_refresh_cache: bool
    gemini_api_key: str | None = None
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket_name: str | None = None
    r2_endpoint_url: str | None = None


def _optional_env(name: str) -> str | None:
    """Return an environment value, treating empty strings as missing."""

    value = getenv(name)
    return value if value else None


def _bool_env(name: str, default: bool = False) -> bool:
    """Return a boolean environment value from common true/false strings."""

    value = getenv(name)

    if value is None:
        return default

    normalized_value = value.strip().lower()

    if normalized_value in {"1", "true", "yes", "y", "on"}:
        return True

    if normalized_value in {"0", "false", "no", "n", "off"}:
        return False

    raise ValueError(
        f"{name} must be a boolean value like true/false, yes/no, or 1/0."
    )


def load_settings() -> AppSettings:
    """Load application settings from .env and environment variables."""

    load_dotenv()

    return AppSettings(
        app_env=getenv("APP_ENV", "local"),
        storage_backend=getenv("STORAGE_BACKEND", "local"),
        local_data_dir=getenv("LOCAL_DATA_DIR", "data"),
        database_url=getenv(
            "DATABASE_URL",
            "postgresql://divinheal:divinheal_dev_password@localhost:5433/divinheal_data",
        ),
        http_timeout_seconds=int(getenv("HTTP_TIMEOUT_SECONDS", "30")),
        http_max_retries=int(getenv("HTTP_MAX_RETRIES", "3")),
        enable_ai_outbound_estimates=_bool_env(
            "ENABLE_AI_OUTBOUND_ESTIMATES",
            default=False,
        ),
        ai_outbound_estimate_max_origins=int(
            getenv("AI_OUTBOUND_ESTIMATE_MAX_ORIGINS", "8")
        ),
        ai_outbound_estimate_refresh_cache=_bool_env(
            "AI_OUTBOUND_ESTIMATE_REFRESH_CACHE",
            default=False,
        ),
        gemini_api_key=_optional_env("GEMINI_API_KEY"),
        r2_account_id=_optional_env("R2_ACCOUNT_ID"),
        r2_access_key_id=_optional_env("R2_ACCESS_KEY_ID"),
        r2_secret_access_key=_optional_env("R2_SECRET_ACCESS_KEY"),
        r2_bucket_name=_optional_env("R2_BUCKET_NAME"),
        r2_endpoint_url=_optional_env("R2_ENDPOINT_URL"),
    )