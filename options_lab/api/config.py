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
        """Fetch secret strictly from environment variables."""
        return os.getenv(secret_id, "")

    # ── AI Model & Round-Robin Load Balancing Pool ────────────────────────────
    @cached_property
    def VERTEX_MODEL(self) -> str:
        return os.getenv("VERTEX_MODEL", "gemini-2.5-flash-lite")

    @cached_property
    def GEMINI_MODEL_POOL(self) -> list:
        """
        Pool of Gemini models used for Round-Robin load balancing and instant failover.
        Prioritizes high-throughput Lite models (15 RPM / 500 RPD) then standard Flash models.
        """
        raw_pool = os.getenv("GEMINI_MODEL_POOL", "")
        if raw_pool:
            return [m.strip() for m in raw_pool.split(",") if m.strip()]
        return [
            "gemini-3.1-flash-lite",
            "gemini-3.5-flash-lite",
            "gemini-3.7-flash",
            "gemini-3.6-flash",
            "gemini-flash-lite-latest",
            "gemini-flash-latest",
            "gemini-2.5-flash"
        ]

    @cached_property
    def GEMINI_API_KEY(self) -> str:
        return self._get_secret("GEMINI_API_KEY")

    @cached_property
    def DISABLE_VERTEX_FALLBACK(self) -> bool:
        return os.getenv("DISABLE_VERTEX_FALLBACK", "false").lower() == "true"

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

    # ── Saxo OpenAPI ──────────────────────────────────────────────────────────
    @cached_property
    def SAXO_ENV(self) -> str:
        """Environment: 'SIM' for Simulation Sandbox or 'LIVE' for Live Production Account."""
        return os.getenv("SAXO_ENV", "SIM").upper()

    @cached_property
    def BROKER_ALLOW_LIVE_EXECUTION(self) -> bool:
        """Safety Shield: Blocks any live order placements unless set to True."""
        return os.getenv("BROKER_ALLOW_LIVE_EXECUTION", "false").lower() == "true"

    @cached_property
    def SAXO_TIMEOUT_SECONDS(self) -> int:
        """HTTP connection and read timeout limit in seconds."""
        return int(os.getenv("SAXO_TIMEOUT_SECONDS", "8"))

    @cached_property
    def SAXO_APP_NAME(self) -> str:
        return os.getenv("SAXO_APP_NAME", "BotAlgoTrade")

    @cached_property
    def SAXO_APP_KEY(self) -> str:
        return self._get_secret("SAXO_APP_KEY") or "996911eb7c6044c5bc9aa5bf50cdf2e9"

    @cached_property
    def SAXO_APP_SECRET(self) -> str:
        return self._get_secret("SAXO_APP_SECRET") or "d5e63c01903b4f70b165b7b800b2a503"

    @cached_property
    def SAXO_APP_SECRET_ALT(self) -> str:
        return self._get_secret("SAXO_APP_SECRET_ALT") or "ef9d31cb1c0b49579c6f34eac7238ad2"

    @cached_property
    def SAXO_ACCESS_TOKEN(self) -> str:
        return self._get_secret("SAXO_ACCESS_TOKEN")

    @cached_property
    def SAXO_REFRESH_TOKEN(self) -> str:
        return self._get_secret("SAXO_REFRESH_TOKEN")


    @cached_property
    def SAXO_AUTH_ENDPOINT(self) -> str:
        if self.SAXO_ENV == "LIVE":
            return os.getenv("SAXO_AUTH_ENDPOINT", "https://live.logonvalidation.net/authorize")
        return os.getenv("SAXO_AUTH_ENDPOINT", "https://sim.logonvalidation.net/authorize")

    @cached_property
    def SAXO_TOKEN_ENDPOINT(self) -> str:
        if self.SAXO_ENV == "LIVE":
            return os.getenv("SAXO_TOKEN_ENDPOINT", "https://live.logonvalidation.net/token")
        return os.getenv("SAXO_TOKEN_ENDPOINT", "https://sim.logonvalidation.net/token")

    @cached_property
    def SAXO_OPENAPI_BASE_URL(self) -> str:
        if self.SAXO_ENV == "LIVE":
            return os.getenv("SAXO_OPENAPI_BASE_URL", "https://gateway.saxobank.com/openapi/")
        return os.getenv("SAXO_OPENAPI_BASE_URL", "https://gateway.saxobank.com/sim/openapi/")

    @cached_property
    def SAXO_REDIRECT_URL(self) -> str:
        return os.getenv("SAXO_REDIRECT_URL", "https://bot-smart.sg.com")

    # ── CORS ──────────────────────────────────────────────────────────────────
    @cached_property
    def CORS_ORIGINS(self) -> list:
        origins = os.getenv("CORS_ORIGINS", "")
        if origins:
            return [o.strip() for o in origins.split(",")]
        return ["*"]

settings = Settings()

