"""
Configuration module with lazy-loaded secrets from GCP Secret Manager.
Falls back to environment variables for local development.
"""

import os
import logging
from functools import cached_property

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)


class Settings:
    """
    Lazy-loaded configuration.
    In production: fetches from GCP Secret Manager.
    Locally: reads from .env file.
    """

    def __init__(self):
        self._project_id = os.getenv("GCP_PROJECT_ID", "")

    # ── GCP ──────────────────────────────────────────────
    @cached_property
    def PROJECT_ID(self) -> str:
        if self._project_id:
            return self._project_id
        try:
            import requests
            resp = requests.get(
                "http://metadata.google.internal/computeMetadata/v1/project/project-id",
                headers={"Metadata-Flavor": "Google"}, timeout=2,
            )
            return resp.text
        except Exception:
            logger.warning("⚠️ Could not resolve GCP Project ID")
            return ""

    # ── Secret Manager helper ────────────────────────────
    def _get_secret(self, secret_id: str) -> str:
        """Fetch secret from GCP Secret Manager, fallback to env var."""
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.PROJECT_ID}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.warning(f"⚠️ Secret '{secret_id}' not in Secret Manager: {e}")
            return os.getenv(secret_id, "")

    # ── Alpaca (OHLCV price data) ────────────────────────
    @cached_property
    def ALPACA_API_KEY(self) -> str:
        return self._get_secret("ALPACA_API_KEY")

    @cached_property
    def ALPACA_SECRET_KEY(self) -> str:
        return self._get_secret("ALPACA_SECRET_KEY")

    # ── Financial Modeling Prep ──────────────────────────
    @cached_property
    def FMP_API_KEY(self) -> str:
        return self._get_secret("FMP_API_KEY")

    # ── FRED ─────────────────────────────────────────────
    @cached_property
    def FRED_API_KEY(self) -> str:
        return self._get_secret("FRED_API_KEY")

    # ── Slack ────────────────────────────────────────────
    @cached_property
    def SLACK_BOT_TOKEN(self) -> str:
        return self._get_secret("SLACK_BOT_TOKEN")

    @cached_property
    def SLACK_SIGNING_SECRET(self) -> str:
        return self._get_secret("SLACK_SIGNING_SECRET")

    @cached_property
    def SLACK_CHANNEL_ID(self) -> str:
        return os.getenv("SLACK_CHANNEL_ID", "")

    @cached_property
    def CRON_SECRET(self) -> str:
        return self._get_secret("CRON_SECRET")

    # ── Email ────────────────────────────────────────────
    @cached_property
    def EMAIL_SENDER(self) -> str:
        return os.getenv("EMAIL_SENDER", "")

    @cached_property
    def EMAIL_APP_PASSWORD(self) -> str:
        return self._get_secret("EMAIL_APP_PASSWORD")

    @cached_property
    def EMAIL_RECIPIENT(self) -> str:
        return os.getenv("EMAIL_RECIPIENT", "")

    # ── Vertex AI ────────────────────────────────────────
    @cached_property
    def VERTEX_MODEL(self) -> str:
        return os.getenv("VERTEX_MODEL", "gemini-2.0-flash-lite")


# Singleton
settings = Settings()
