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
    r2_account_id: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None
    r2_bucket_name: str | None = None
    r2_endpoint_url: str | None = None


def _optional_env(name: str) -> str | None:
    """Return an environment value, treating empty strings as missing."""

    value = getenv(name)
    return value if value else None


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
        r2_account_id=_optional_env("R2_ACCOUNT_ID"),
        r2_access_key_id=_optional_env("R2_ACCESS_KEY_ID"),
        r2_secret_access_key=_optional_env("R2_SECRET_ACCESS_KEY"),
        r2_bucket_name=_optional_env("R2_BUCKET_NAME"),
        r2_endpoint_url=_optional_env("R2_ENDPOINT_URL"),
    )