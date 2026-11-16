"""The authentication seam.

The rest of the server only knows this protocol, so swapping the local password
provider for an account backend does not touch routes or the workspace store.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

User = dict[str, Any]


@runtime_checkable
class AuthProvider(Protocol):
    async def sign_up(self, name: str, email: str, password: str) -> User: ...

    async def sign_in(self, email: str, password: str) -> User: ...

    async def sign_out(self, token: str | None = None) -> None: ...

    async def current_user(self, token: str | None) -> User | None: ...


class AuthError(Exception):
    """A friendly authentication failure."""

    def __init__(self, message: str, status_code: int = 400) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
