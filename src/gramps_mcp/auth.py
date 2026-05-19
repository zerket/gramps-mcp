import time
import asyncio
import httpx
from gramps_mcp.config import settings


class AuthManager:
    """Manages JWT tokens for Gramps Web API.

    - Caches access + refresh tokens
    - Proactively refreshes 30s before expiry
    - Retries on 401 with fresh credentials
    - Thread-safe via asyncio.Lock
    """

    def __init__(self) -> None:
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0.0
        self._lock = asyncio.Lock()

    async def _post_token(self, endpoint: str, data: dict) -> str | None:
        """POST to /api/token/ or /api/token/refresh/ — returns error string or None."""
        url = f"{settings.gramps_api_url}/api/token/{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
                resp = await client.post(url, json=data)
                if resp.status_code == 200:
                    payload = resp.json()
                    token: str | None = payload.get("access_token")
                    if not token:
                        return "Auth error: No access_token in response"
                    self._access_token = token
                    self._refresh_token = payload.get("refresh_token")
                    expires_in = self._decode_exp(token)
                    self._expires_at = time.time() + expires_in - 30  # 30s buffer
                    return None
                return f"Auth error: HTTP {resp.status_code} — {resp.text}"
        except httpx.RequestError as e:
            return f"Auth error: Cannot connect to {settings.gramps_api_url} — {e}"

    async def authenticate(self) -> str | None:
        """Log in with username/password, store tokens."""
        error = await self._post_token("", {
            "username": settings.gramps_username,
            "password": settings.gramps_password,
        })
        return error

    async def refresh(self) -> str | None:
        """Refresh access token using refresh token."""
        if not self._refresh_token:
            return await self.authenticate()
        error = await self._post_token("refresh/", {
            "refresh_token": self._refresh_token,
        })
        if error:
            # Refresh failed — try full login
            return await self.authenticate()
        return None

    def invalidate(self) -> None:
        """Clear cached tokens (called on 401 before retry)."""
        self._access_token = None
        self._refresh_token = None
        self._expires_at = 0.0

    async def get_valid_token(self) -> str:
        """Return a valid access token, refreshing or authenticating as needed."""
        async with self._lock:
            # Check if cached token is still valid (with 30s buffer)
            if self._access_token and time.time() < self._expires_at:
                return self._access_token

            # Token expired or missing — refresh or re-authenticate
            if self._refresh_token:
                error = await self.refresh()
            else:
                error = await self.authenticate()

            if error:
                return error  # error string
            return self._access_token or "Auth error: Failed to obtain token"

    @staticmethod
    def _decode_exp(token: str) -> int:
        """Decode JWT exp claim without verification."""
        import base64
        import json
        try:
            # JWT: header.payload.signature
            payload_b64 = token.split(".")[1]
            # Add padding
            payload_b64 += "=" * (4 - len(payload_b64) % 4)
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            return int(payload.get("exp", 900))  # default 15 min
        except Exception:
            return 900  # fallback: 15 minutes
