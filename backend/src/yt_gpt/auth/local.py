"""Local password profiles backed by files under ``~/.yt-gpt/users``."""

from __future__ import annotations

import asyncio
import re
import uuid
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from .. import config
from ..util import atomic_write_text, ensure_private, read_json, write_json
from .base import AuthError, User

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
MIN_PASSWORD = 6


def public_user(profile: dict) -> User:
    return {
        "id": profile.get("id", ""),
        "email": profile.get("email", ""),
        "name": profile.get("name", ""),
        "createdAt": profile.get("created_at", ""),
    }


class LocalAuthProvider:
    def __init__(self, root: Path | None = None) -> None:
        self.root = root or config.users_root()
        self._lock = asyncio.Lock()
        self._hasher = PasswordHasher()

    def _profile_path(self, user_id: str) -> Path:
        return self.root / user_id / "profile.json"

    def _find_by_email(self, email: str) -> dict | None:
        target = email.strip().lower()
        if not self.root.exists():
            return None
        for child in self.root.iterdir():
            if not child.is_dir():
                continue
            profile = read_json(child / "profile.json")
            if isinstance(profile, dict) and str(profile.get("email", "")).lower() == target:
                return profile
        return None

    async def sign_up(self, name: str, email: str, password: str) -> User:
        clean_name = (name or "").strip()
        clean_email = (email or "").strip().lower()
        if not clean_name:
            raise AuthError("Add a display name.")
        if not EMAIL_RE.match(clean_email):
            raise AuthError("That email does not look right.")
        if len(password or "") < MIN_PASSWORD:
            raise AuthError(f"Use at least {MIN_PASSWORD} characters for the password.")

        async with self._lock:
            if self._find_by_email(clean_email):
                raise AuthError("A profile already uses that email.", 409)
            user_id = f"u_{uuid.uuid4().hex[:12]}"
            user_dir = self.root / user_id
            user_dir.mkdir(parents=True, exist_ok=True)
            profile = {
                "id": user_id,
                "email": clean_email,
                "name": clean_name,
                "created_at": _now(),
                "password_hash": await asyncio.to_thread(self._hasher.hash, password),
            }
            path = self._profile_path(user_id)
            write_json(path, profile)
            ensure_private(path)
            (user_dir / "workspaces").mkdir(parents=True, exist_ok=True)
            return public_user(profile)

    async def sign_in(self, email: str, password: str) -> User:
        clean_email = (email or "").strip().lower()
        async with self._lock:
            profile = await asyncio.to_thread(self._find_by_email, clean_email)
            if not profile:
                raise AuthError("Email or password is wrong.", 401)
            password_hash = profile.get("password_hash")
            if not password_hash:
                raise AuthError("This profile has no password.", 401)
            try:
                await asyncio.to_thread(self._hasher.verify, password_hash, password)
            except VerifyMismatchError:
                raise AuthError("Email or password is wrong.", 401) from None
            except Exception:
                raise AuthError("Email or password is wrong.", 401) from None
            return public_user(profile)

    async def sign_out(self, token: str | None = None) -> None:
        return None

    async def current_user(self, token: str | None) -> User | None:
        if not token:
            return None
        if not token.startswith("u_") or any(
            ch not in "abcdefghijklmnopqrstuvwxyz0123456789_" for ch in token
        ):
            return None
        profile = await asyncio.to_thread(read_json, self._profile_path(token))
        if not isinstance(profile, dict):
            return None
        return public_user(profile)

    async def get_profile(self, user_id: str) -> dict | None:
        profile = await asyncio.to_thread(read_json, self._profile_path(user_id))
        return profile if isinstance(profile, dict) else None


def _now() -> str:
    from ..util import iso_now

    return iso_now()


__all__ = ["LocalAuthProvider", "public_user", "atomic_write_text"]
