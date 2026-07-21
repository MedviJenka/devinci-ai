"""Shared constants used by both the root conftest.py (server lifecycle) and
the e2e test conftest.py (route mocking). Kept dependency-free and import-safe
from either side of that split.
"""
from pathlib import Path
import tempfile

# Matches the default in frontend/src/api.ts (REACT_APP_API_BASE is unset in
# the build used for tests). Playwright intercepts every request under this
# origin, so nothing needs to actually be listening on localhost:5555.
API_BASE = "http://localhost:5555/api/v1/npcs"

# Real project ref from frontend/.env, used only to scope Playwright route
# mocks for Supabase auth calls -- no request ever reaches the real project.
SUPABASE_URL = "https://vzfnmqywgvfnyeoobrfs.supabase.co"

STATE_FILE = Path(tempfile.gettempdir()) / "interactive_npc_e2e_frontend_server.json"
