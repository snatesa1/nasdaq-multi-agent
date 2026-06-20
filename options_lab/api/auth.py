"""
auth.py — Firebase JWT verification for OptionsLab API.

Verifies the Firebase ID token from the Authorization header
using Google's public keys (no firebase-admin SDK needed, lighter).
Falls back to allowing unauthenticated requests in dev mode.
"""

import logging
import os
from typing import Optional, Dict, Any

from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

logger = logging.getLogger(__name__)

security = HTTPBearer(auto_error=False)

# In production, verify tokens. In dev, allow bypass.
_AUTH_DISABLED = os.getenv("DISABLE_AUTH", "false").lower() == "true"


async def verify_firebase_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[Dict[str, Any]]:
    """
    FastAPI dependency that verifies a Firebase ID token.

    Returns the decoded token payload (with uid, email, etc.) or None if
    auth is disabled for development.

    Raises HTTPException 401 if the token is invalid or missing in production.
    """
    if _AUTH_DISABLED:
        return {"uid": "dev-user", "email": "dev@local", "name": "Dev User"}

    if credentials is None:
        raise HTTPException(status_code=401, detail="Authorization header missing")

    token = credentials.credentials

    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        # Verify the Firebase ID token using Google's public keys
        # Firebase tokens are signed by Google and can be verified
        # against securetoken.google.com
        decoded = id_token.verify_firebase_token(
            token,
            google_requests.Request(),
            audience=os.getenv("FIREBASE_PROJECT_ID", "optimal-aurora-495912-n0"),
        )

        logger.info(f"Authenticated user: {decoded.get('email', decoded.get('sub'))}")
        return decoded

    except ValueError as e:
        logger.warning(f"Invalid Firebase token: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except Exception as e:
        logger.error(f"Token verification failed: {e}")
        raise HTTPException(status_code=401, detail="Authentication failed")
