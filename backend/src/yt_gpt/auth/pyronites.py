"""Optional Pyronites account provider.

The provider is intentionally lazy: the package is only needed when a user
selects ``[auth] provider = "pyronites"`` in ``config.toml``. The local provider
remains the default so a fresh install still works offline.
"""

from __future__ import annotations

import os

from .base import AuthError, User


class PyronitesAuthProvider:
    def __init__(self, url: str | None = None, api_key: str | None = None) -> None:
        self.url = url or os.environ.get("PYRONITES_URL", "")
        self.api_key = api_key or os.environ.get("PYRONITES_KEY", "")
        self._client = None

    def _ensure_client(self):
        if self._client is not None:
            return self._client
        if not self.url or not self.api_key:
            raise AuthError(
                "Pyronites auth needs PYRONITES_URL and PYRONITES_KEY (or the same values in config.toml).",
                500,
            )
        try:
            from pyronites import create_client  # type: ignore[import-not-found]
        except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
            raise AuthError(
                "Pyronites auth is selected but the pyronites package is not installed. "
                'Install it with `pip install "yt-gpt[pyronites]"` or switch to local auth.',
                500,
            ) from exc
        self._client = create_client(url=self.url, api_key=self.api_key)
        return self._client

    @staticmethod
    def _to_user(raw) -> User:
        if isinstance(raw, dict):
            data = raw
        else:
            data = {
                "id": getattr(raw, "id", ""),
                "email": getattr(raw, "email", ""),
                "name": getattr(raw, "name", getattr(raw, "email", "")),
                "created_at": getattr(raw, "created_at", ""),
            }
        return {
            "id": str(data.get("id", "")),
            "email": str(data.get("email", "")),
            "name": str(data.get("name", data.get("email", ""))),
            "createdAt": str(data.get("created_at", data.get("createdAt", ""))),
        }

    async def sign_up(self, name: str, email: str, password: str) -> User:
        client = self._ensure_client()
        try:
            raw = client.auth.sign_up(email=email, password=password, name=name)
        except Exception as exc:  # pragma: no cover - remote backend
            raise AuthError(str(exc) or "Pyronites sign-up failed.", 400) from exc
        return self._to_user(raw)

    async def sign_in(self, email: str, password: str) -> User:
        client = self._ensure_client()
        try:
            raw = client.auth.sign_in(email=email, password=password)
        except Exception as exc:  # pragma: no cover - remote backend
            raise AuthError(str(exc) or "Email or password is wrong.", 401) from exc
        return self._to_user(raw)

    async def sign_out(self, token: str | None = None) -> None:
        return None

    async def current_user(self, token: str | None) -> User | None:
        if not token:
            return None
        client = self._ensure_client()
        try:
            raw = client.auth.user(token=token)
        except Exception:  # pragma: no cover - remote backend
            return None
        return self._to_user(raw) if raw else None
