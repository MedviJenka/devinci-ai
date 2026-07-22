"""
Fixtures for backend API tests under tests/token.

Unlike tests/e2e (which mocks Supabase auth at the Playwright network layer),
these tests exercise the real FastAPI auth dependency
(core.useful.auth.get_current_user_id), which validates a bearer token
against the real Supabase project via `db.auth.get_user(jwt)`. So the token
handed to these tests has to be one Supabase actually issued.
"""
from __future__ import annotations

import uuid
from typing import Iterator

import pytest
from supabase import create_client

from core.settings import Config, db


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

    created = db.auth.admin.create_user(
        {"email": email, "password": password, "email_confirm": True}
    )
    user_id = created.user.id

    try:
        anon_client = create_client(Config.SUPABASE_URL, Config.SUPABASE_PUBLISHABLE_API_KEY)
        session = anon_client.auth.sign_in_with_password({"email": email, "password": password})
        yield session.session.access_token
    finally:
        db.auth.admin.delete_user(user_id)
