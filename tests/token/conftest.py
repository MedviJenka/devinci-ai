"""
Fixtures for backend API tests under tests/token.

Unlike tests/e2e (which mocks Supabase auth at the Playwright network layer),
these tests exercise the real FastAPI auth dependency
(core.useful.auth.get_current_user_id), which validates a bearer token
against the real Supabase project via `db.auth.get_user(jwt)`. So the token
handed to these tests has to be one Supabase actually issued.
"""
from __future__ import annotations

import time
import uuid
from typing import Callable, Iterator, TypeVar

import pytest
from supabase import create_client
from supabase_auth.errors import AuthApiError

from core.settings import Config, db

T = TypeVar("T")


def _retry_bad_jwt(call: Callable[[], T], *, attempts: int = 5, delay: float = 0.5) -> T:
    """Retry admin auth calls against Supabase's own service-role key.

    The Supabase-hosted auth server intermittently (and non-deterministically,
    confirmed by hammering the REST endpoint directly with curl) responds to a
    valid `sb_secret_...` bearer token with `{"error_code": "bad_jwt"}` --
    roughly one in three calls fails this way and immediately succeeds on
    retry. This is transient flakiness in Supabase's key verification, not a
    bug in our request, so retrying is the correct fix rather than reworking
    how the request is built.
    """
    last_error: AuthApiError | None = None
    for attempt in range(attempts):
        try:
            return call()
        except AuthApiError as exc:
            if "bad_jwt" not in str(exc) and getattr(exc, "code", None) != "bad_jwt":
                raise
            last_error = exc
            if attempt < attempts - 1:
                time.sleep(delay)
    assert last_error is not None
    raise last_error


@pytest.fixture
def test_token() -> Iterator[str]:
    """Create a throwaway Supabase user and return a real access token for it.

    Yields the token, then deletes the user afterwards so test runs don't
    accumulate throwaway accounts in the project.

    Signing in is done through a separate anon-key client rather than the
    shared service-role `db` client: `db.auth` is a single stateful client,
    and calling sign_in_with_password on it would overwrite its session with
    the throwaway user's, breaking the admin calls (create_user/delete_user)
    that need the service-role session.
    """
    email = f"e2e-{uuid.uuid4().hex}@example.com"
    password = uuid.uuid4().hex

    created = _retry_bad_jwt(
        lambda: db.auth.admin.create_user(
            {"email": email, "password": password, "email_confirm": True}
        )
    )
    user_id = created.user.id

    try:
        anon_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_PUBLISHABLE_API_KEY)
        session = anon_client.auth.sign_in_with_password({"email": email, "password": password})
        yield session.session.access_token
    finally:
        _retry_bad_jwt(lambda: db.auth.admin.delete_user(user_id))
