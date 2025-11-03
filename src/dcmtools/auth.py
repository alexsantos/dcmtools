import json
import time
from threading import Lock
from typing import Optional, Tuple

import requests

class TokenManager:
    """
    Bearer token manager:
      - static token (no refresh)
      - OAuth2 client credentials (auto-refresh via expires_in or JWT exp)
    Thread-safe for concurrent use.
    """
    def __init__(
        self,
        static_token: Optional[str],
        token_endpoint: Optional[str],
        client_id: Optional[str],
        client_secret: Optional[str],
        scope: Optional[str] = None,
        skew_seconds: int = 60,
        insecure: bool = False,
        timeout: int = 30,
    ):
        self.static_token = static_token
        self.token_endpoint = token_endpoint
        self.client_id = client_id
        self.client_secret = client_secret
        self.scope = scope
        self.skew = skew_seconds
        self.insecure = insecure
        self.timeout = timeout
        self._token: Optional[str] = static_token
        self._exp_ts: Optional[float] = None
        self._lock = Lock()

    @staticmethod
    def _decode_jwt_exp(token: str) -> Optional[int]:
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            import base64
            def b64pad(s: str) -> str:
                return s + "=" * ((4 - len(s) % 4) % 4)
            payload = json.loads(base64.urlsafe_b64decode(b64pad(parts[1])).decode("utf-8"))
            return int(payload.get("exp")) if "exp" in payload else None
        except Exception:
            return None

    def _fetch_token(self) -> Tuple[str, Optional[float]]:
        if not self.token_endpoint or not self.client_id or not self.client_secret:
            raise RuntimeError("Token endpoint/client_id/client_secret required for OAuth2 refresh.")
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
        }
        if self.scope:
            data["scope"] = self.scope
        resp = requests.post(self.token_endpoint, data=data, timeout=self.timeout, verify=not self.insecure)
        resp.raise_for_status()
        tok = resp.json()
        access = tok.get("access_token") or tok.get("token")
        if not access:
            raise RuntimeError(f"Token endpoint did not return access_token. Body: {tok}")
        exp = self._decode_jwt_exp(access)
        if exp is None:
            expires_in = tok.get("expires_in")
            exp = time.time() + int(expires_in) if expires_in else None
        return access, exp

    def get(self, force_refresh: bool = False) -> str:
        if self.static_token:
            return self.static_token
        with self._lock:
            needs = force_refresh or (self._token is None) or (
                self._exp_ts and (time.time() + self.skew) >= self._exp_ts
            )
            if needs:
                token, exp = self._fetch_token()
                self._token, self._exp_ts = token, exp
            return self._token  # type: ignore[return-value]
