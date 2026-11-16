"""Configuration directory, config.toml and the cookie-signing secret."""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from pathlib import Path

try:  # Python 3.11+
    import tomllib as _toml
except ModuleNotFoundError:  # pragma: no cover - 3.10
    import tomli as _toml  # type: ignore[import-not-found,no-redef]

import tomli_w

from .util import ensure_private, read_json

CONFIG_FILENAME = "config.toml"
SECRET_FILENAME = ".secret"
DEFAULT_PORT = 8765
DEFAULT_HOST = "127.0.0.1"


def home() -> Path:
    override = os.environ.get("YT_GPT_HOME")
    if override:
        return Path(override).expanduser().resolve()
    return (Path.home() / ".yt-gpt").resolve()


def ensure_home() -> Path:
    root = home()
    for child in ("users", "secrets", "trash"):
        (root / child).mkdir(parents=True, exist_ok=True)
    return root


def users_root() -> Path:
    return home() / "users"


def user_root(user_id: str) -> Path:
    if not user_id:
        raise ValueError("user id is required")
    return users_root() / user_id


def workspaces_root(user_id: str) -> Path:
    return user_root(user_id) / "workspaces"


def secrets_root() -> Path:
    return home() / "secrets"


@dataclass(slots=True)
class AppConfig:
    host: str = DEFAULT_HOST
    port: int = DEFAULT_PORT
    auth_provider: str = "local"
    open_browser: bool = True
    cookies_file: str | None = None
    log_level: str = "info"

    @property
    def root(self) -> Path:
        return home()


def config_path() -> Path:
    return home() / CONFIG_FILENAME


def load_config() -> AppConfig:
    path = config_path()
    data: dict = {}
    try:
        with path.open("rb") as handle:
            data = _toml.load(handle)
    except (OSError, ValueError):
        data = {}
    server = data.get("server", {}) if isinstance(data, dict) else {}
    auth = data.get("auth", {}) if isinstance(data, dict) else {}
    ingest = data.get("ingest", {}) if isinstance(data, dict) else {}
    return AppConfig(
        host=str(server.get("host", DEFAULT_HOST)),
        port=int(server.get("port", DEFAULT_PORT)),
        auth_provider=str(auth.get("provider", "local")),
        open_browser=bool(server.get("open_browser", True)),
        cookies_file=ingest.get("cookies_file"),
        log_level=str(server.get("log_level", "info")),
    )


def save_config(config: AppConfig) -> None:
    ensure_home()
    data = {
        "server": {
            "host": config.host,
            "port": config.port,
            "open_browser": config.open_browser,
            "log_level": config.log_level,
        },
        "auth": {"provider": config.auth_provider},
        "ingest": {"cookies_file": config.cookies_file},
    }
    from .util import atomic_write_text

    atomic_write_text(config_path(), tomli_w.dumps(data))


def cookies_file() -> Path | None:
    env = os.environ.get("YT_GPT_COOKIES")
    if env:
        path = Path(env).expanduser()
        return path if path.exists() else None
    configured = load_config().cookies_file
    if configured:
        path = Path(configured).expanduser()
        if path.exists():
            return path
    default = home() / "cookies.txt"
    return default if default.exists() else None


_SECRET_CACHE: str | None = None


def secret_key() -> str:
    """Return a stable signing secret, creating one on first run."""
    global _SECRET_CACHE
    if _SECRET_CACHE:
        return _SECRET_CACHE
    env = os.environ.get("YT_GPT_SECRET")
    if env:
        _SECRET_CACHE = env
        return env
    ensure_home()
    path = home() / SECRET_FILENAME
    if path.exists():
        try:
            value = path.read_text(encoding="utf-8").strip()
            if value:
                _SECRET_CACHE = value
                return value
        except OSError:
            pass
    value = secrets.token_urlsafe(48)
    from .util import atomic_write_text

    atomic_write_text(path, value + "\n")
    ensure_private(path)
    _SECRET_CACHE = value
    return value


def local_user_profiles() -> list[dict]:
    root = users_root()
    if not root.exists():
        return []
    profiles: list[dict] = []
    for child in sorted(root.iterdir()):
        if not child.is_dir():
            continue
        profile = read_json(child / "profile.json")
        if isinstance(profile, dict):
            profiles.append(profile)
    return profiles
