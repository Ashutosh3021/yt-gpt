"""A tiny HMAC-signed cookie session, no middleware needed."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from .. import config

COOKIE_NAME = "yt_gpt_session"
MAX_AGE = 60 * 60 * 24 * 30


def _sign(payload: str) -> str:
    key = config.secret_key().encode("utf-8")
    return hmac.new(key, payload.encode("utf-8"), hashlib.sha256).hexdigest()


def encode_session(user_id: str) -> str:
    body = {"uid": user_id, "iat": int(time.time())}
    payload = base64.urlsafe_b64encode(json.dumps(body, separators=(",", ":")).encode("utf-8")).decode(
        "ascii"
    )
    return f"{payload}.{_sign(payload)}"


def decode_session(value: str | None) -> dict[str, Any] | None:
    if not value or "." not in value:
        return None
    payload, signature = value.rsplit(".", 1)
    if not hmac.compare_digest(signature, _sign(payload)):
        return None
    try:
        raw = base64.urlsafe_b64decode(payload.encode("ascii"))
        data = json.loads(raw)
    except (ValueError, TypeError):
        return None
    if not isinstance(data, dict) or not isinstance(data.get("uid"), str):
        return None
    issued = data.get("iat")
    if isinstance(issued, int) and time.time() - issued > MAX_AGE:
        return None
    return data


def set_session_cookie(response: Any, user_id: str) -> None:
    response.set_cookie(
        COOKIE_NAME,
        encode_session(user_id),
        max_age=MAX_AGE,
        httponly=True,
        samesite="strict",
        path="/",
    )


def clear_session_cookie(response: Any) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")
