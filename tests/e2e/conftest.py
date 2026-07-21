"""
Fixtures for the Playwright E2E suite.

Every test gets its own `page` (from pytest-playwright, function-scoped by
default), so tests are isolated from each other and safe to run under
`pytest -n auto`. Nothing here shares mutable state across tests -- the only
shared resource is the read-only static file server started in the root
conftest.py's `pytest_configure`.

Two boundaries are mocked at the Playwright network layer, never touching a
real backend or the real Supabase project:
  - the NPC REST API (frontend/src/api.ts, http://localhost:5555/api/v1/npcs)
  - Supabase auth (frontend/src/supabaseClient.ts)

Both origins are cross-origin from the static server's own origin, and the
app always sends a `Content-Type: application/json` header, which forces a
CORS preflight for every request (GET included). So every mocked response
below carries explicit CORS headers -- Playwright intercepts the network
call, but the browser's own CORS enforcement still applies to what we hand
back.
"""

import json
import re
import time
import pytest
from dataclasses import dataclass, field
from tests.e2e.mock_constants import API_BASE, STATE_FILE, SUPABASE_URL


# ---------------------------------------------------------------------------
# Shared static server discovery
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def frontend_base_url() -> str:
    deadline = time.time() + 30
    while time.time() < deadline:
        if STATE_FILE.exists():
            info = json.loads(STATE_FILE.read_text())
            return info["base_url"]
        time.sleep(0.2)
    raise RuntimeError(
        f"{STATE_FILE} was never written -- the root conftest.py's "
        "pytest_configure hook should have started the frontend server."
    )


def _cors_headers(request) -> dict:
    origin = request.headers.get("origin", "*")
    return {
        "Access-Control-Allow-Origin": origin,
        "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type, Authorization, apikey, x-client-info",
        "Access-Control-Allow-Credentials": "true",
        "Vary": "Origin",
    }


def _json(route, request, status: int, payload) -> None:
    route.fulfill(
        status=status,
        headers={**_cors_headers(request), "Content-Type": "application/json"},
        body=json.dumps(payload),
    )


def _slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")
    return slug or "npc"


# ---------------------------------------------------------------------------
# NPC REST API mock
# ---------------------------------------------------------------------------

@dataclass
class NpcApiMock:
    """In-memory fake of the FastAPI NPC endpoints, scoped to a single test."""

    npcs: dict = field(default_factory=dict)  # slug -> detail dict
    stream_events: list | None = None  # override the /talk SSE script
    talk_requests: list = field(default_factory=list)  # recorded (slug, query) pairs

    def seed(self, *, slug: str, role: str, goal="", backstory="", llm="gpt-4o", persona_notes=""):
        detail = {
            "slug": slug,
            "role": role,
            "goal": goal,
            "backstory": backstory,
            "llm": llm,
            "persona_notes": persona_notes,
        }
        self.npcs[slug] = detail
        return detail

    def summaries(self):
        return [
            {"slug": n["slug"], "role": n["role"], "goal": n["goal"], "llm": n["llm"]}
            for n in self.npcs.values()
        ]


def _install_npc_api_routes(page, mock: NpcApiMock) -> None:
    def handler(route):
        request = route.request
        if request.method == "OPTIONS":
            route.fulfill(status=204, headers=_cors_headers(request))
            return

        path = request.url[len(API_BASE):]
        path = path.split("?", 1)[0]

        if path == "/" and request.method == "GET":
            _json(route, request, 200, mock.summaries())
            return

        if path == "/" and request.method == "POST":
            payload = json.loads(request.post_data or "{}")
            slug = _slugify(payload["name"])
            detail = mock.seed(
                slug=slug,
                role=payload["name"],
                goal=payload.get("goal") or "",
                backstory=payload.get("backstory") or "",
                llm=payload.get("llm") or "gpt-4o",
                persona_notes=payload.get("persona_notes") or "",
            )
            _json(route, request, 201, detail)
            return

        if path.endswith("/talk"):
            slug = path[1:-len("/talk")]
            query_params = dict(
                pair.split("=", 1) for pair in request.url.split("?", 1)[1].split("&") if "=" in pair
            ) if "?" in request.url else {}
            from urllib.parse import unquote_plus

            query_text = unquote_plus(query_params.get("query", ""))
            mock.talk_requests.append((slug, query_text))

            events = mock.stream_events
            if events is None:
                events = [
                    {"type": "chunk", "text": "..."},
                    {
                        "type": "done",
                        "text": json.dumps({"response": f"Echo: {query_text}"}),
                        "mood": "neutral",
                    },
                ]
            body = "".join(f"data: {json.dumps(e)}\n\n" for e in events)
            route.fulfill(
                status=200,
                headers={**_cors_headers(request), "Content-Type": "text/event-stream"},
                body=body,
            )
            return

        slug = path[1:]
        if request.method == "GET":
            detail = mock.npcs.get(slug)
            if detail is None:
                _json(route, request, 404, {"detail": "not found"})
            else:
                _json(route, request, 200, detail)
            return

        if request.method == "PUT":
            payload = json.loads(request.post_data or "{}")
            detail = mock.npcs[slug]
            detail.update({k: v for k, v in payload.items() if v is not None})
            _json(route, request, 200, detail)
            return

        if request.method == "DELETE":
            mock.npcs.pop(slug, None)
            route.fulfill(status=204, headers=_cors_headers(request), body="")
            return

        route.fallback()

    page.route(f"{API_BASE}/**", handler)


@pytest.fixture
def npc_api(page) -> NpcApiMock:
    mock = NpcApiMock()
    _install_npc_api_routes(page, mock)
    return mock


# ---------------------------------------------------------------------------
# Supabase auth mock
# ---------------------------------------------------------------------------

FAKE_SESSION_USER = {
    "id": "00000000-0000-0000-0000-000000000001",
    "email": "player@example.com",
    "app_metadata": {},
    "user_metadata": {},
    "aud": "authenticated",
}


def _fake_session_body() -> dict:
    return {
        "access_token": "e2e-fake-access-token",
        "token_type": "bearer",
        "expires_in": 3600,
        "expires_at": int(time.time()) + 3600,
        "refresh_token": "e2e-fake-refresh-token",
        "user": FAKE_SESSION_USER,
    }


@dataclass
class AuthMock:
    otp_calls: list = field(default_factory=list)
    verify_calls: list = field(default_factory=list)
    verify_should_fail: bool = False


def _install_auth_routes(page, mock: AuthMock) -> None:
    def handler(route):
        request = route.request
        if request.method == "OPTIONS":
            route.fulfill(status=204, headers=_cors_headers(request))
            return

        path = request.url.split("?", 1)[0][len(SUPABASE_URL):]

        if path == "/auth/v1/otp":
            mock.otp_calls.append(json.loads(request.post_data or "{}"))
            _json(route, request, 200, {})
            return

        if path == "/auth/v1/verify":
            mock.verify_calls.append(json.loads(request.post_data or "{}"))
            if mock.verify_should_fail:
                _json(route, request, 400, {"error": "invalid_otp", "error_description": "Token has expired or is invalid"})
            else:
                _json(route, request, 200, _fake_session_body())
            return

        if path == "/auth/v1/token":
            _json(route, request, 200, _fake_session_body())
            return

        if path == "/auth/v1/logout":
            route.fulfill(status=204, headers=_cors_headers(request), body="")
            return

        if path == "/auth/v1/authorize":
            # Real OAuth requires leaving the app for Google's consent screen;
            # E2E coverage stops at "the app attempted the redirect" (see
            # test_sign_in.py::test_google_button_starts_oauth_redirect).
            route.fulfill(status=200, headers=_cors_headers(request), body="")
            return

        route.fallback()

    page.route(f"{SUPABASE_URL}/**", handler)


@pytest.fixture
def auth_mock(page) -> AuthMock:
    mock = AuthMock()
    _install_auth_routes(page, mock)
    return mock


# ---------------------------------------------------------------------------
# Signed-in app shell
# ---------------------------------------------------------------------------

@dataclass
class AppDriver:
    """Bundles a page with its mocks and defers sign-in until the test calls
    it explicitly. This matters because App's post-login useEffect fires
    listNpcs() the instant a session appears -- if sign-in happened
    automatically inside a fixture, tests would have no chance to call
    `npc_api.seed(...)` first, and would always see an empty roster on
    first render."""

    page: object
    npc_api: NpcApiMock
    auth_mock: AuthMock
    base_url: str

    def sign_in(self, email: str = "player@example.com") -> None:
        page = self.page
        page.goto(self.base_url)

        page.get_by_placeholder("you@example.com").fill(email)
        page.get_by_role("button", name=re.compile("send code", re.I)).click()

        digit_inputs = page.locator("input[inputmode='numeric']")
        digit_inputs.first.wait_for(state="visible")
        for i, digit in enumerate("123456"):
            digit_inputs.nth(i).fill(digit)

        page.get_by_role("button", name=re.compile("verify", re.I)).click()
        # "New NPC" only renders once the authenticated app shell (Sidebar) mounts.
        page.get_by_role("button", name=re.compile("new npc", re.I)).wait_for(state="visible")

    def nav(self, label: str) -> None:
        """Sidebar items are plain <div onClick> elements, not buttons, so
        they need a text locator rather than get_by_role. Scoped to the
        label span specifically (not just <nav>): the material icon next to
        it renders its ligature name as literal text too (e.g. the Dashboard
        icon's text content is "dashboard"), which collides with the "^...$"
        match against the nav item's own label."""
        self.page.locator("nav span.font-label-caps").filter(
            has_text=re.compile(f"^{re.escape(label)}$", re.I)
        ).click()


@pytest.fixture
def app(page, frontend_base_url, auth_mock, npc_api) -> AppDriver:
    """Drives the real SignIn UI (email -> OTP) against mocked network calls.
    Seed `app.npc_api` before calling `app.sign_in()` if a test needs
    existing NPCs to be present on first load."""
    return AppDriver(page=page, npc_api=npc_api, auth_mock=auth_mock, base_url=frontend_base_url)
