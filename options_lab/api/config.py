import os
import logging
from functools import cached_property
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class Settings:
    """
    Configuration settings for OptionsLab backend.
    Unified config covering options engine, multi-agent pipeline,
    portfolio sync, and authentication.
    """
    def __init__(self):
        self._project_id = os.getenv("GCP_PROJECT_ID", "")

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
            return "optimal-aurora-495912-n0"

    def _get_secret(self, secret_id: str) -> str:
        """Fetch secret from env var first, falling back to GCP Secret Manager."""
        val = os.getenv(secret_id, "")
        if val:
            return val
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.PROJECT_ID}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8").strip()
        except Exception:
            return ""

    # ── AI Model ──────────────────────────────────────────────────────────────
    @cached_property
    def VERTEX_MODEL(self) -> str:
        return os.getenv("VERTEX_MODEL", "gemini-2.5-flash")

    @cached_property
    def GEMINI_API_KEY(self) -> str:
        return self._get_secret("GEMINI_API_KEY")

    # ── Market Data API Keys ──────────────────────────────────────────────────
    @cached_property
    def ALPACA_API_KEY(self) -> str:
        return self._get_secret("ALPACA_API_KEY")

    @cached_property
    def ALPACA_SECRET_KEY(self) -> str:
        return self._get_secret("ALPACA_SECRET_KEY")

    @cached_property
    def FMP_API_KEY(self) -> str:
        return self._get_secret("FMP_API_KEY")

    @cached_property
    def FRED_API_KEY(self) -> str:
        return self._get_secret("FRED_API_KEY")

    # ── Authentication ────────────────────────────────────────────────────────
    @cached_property
    def GOOGLE_CLIENT_ID(self) -> str:
        return self._get_secret("GOOGLE_CLIENT_ID")

    @cached_property
    def FIREBASE_PROJECT_ID(self) -> str:
        """Firebase project ID (usually same as GCP project ID)."""
        return os.getenv("FIREBASE_PROJECT_ID", self.PROJECT_ID)

    # ── CORS ──────────────────────────────────────────────────────────────────
    @cached_property
    def CORS_ORIGINS(self) -> list:
        origins = os.getenv("CORS_ORIGINS", "")
        if origins:
            return [o.strip() for o in origins.split(",")]
        return ["*"]

settings = Settings()
