import re

import pytest

pytestmark = pytest.mark.e2e


def _generate_key(app, name: str = "Test Key"):
    page = app.page
    app.nav("API Keys")
    page.get_by_role("button", name=re.compile("generate first key", re.I)).click()
    page.get_by_placeholder(re.compile("production_orchestrator", re.I)).fill(name)
    page.get_by_role("button", name=re.compile("^generate$", re.I)).click()
    page.get_by_text(name).wait_for(state="visible")


@pytest.mark.smoke
def test_generate_key_shows_masked_value(app):
    app.sign_in()
    _generate_key(app)
    # The table only ever shows key_prefix (`dv_` + 8 hex chars, see
    # src/core/database/api_keys/client.py) with 16 bullets appended -- the raw
    # key itself is never persisted or re-fetchable.
    app.page.get_by_text(re.compile(r"^dv_[0-9a-f]{8}•{16}$")).wait_for(state="visible")


@pytest.mark.regression
def test_creation_banner_shows_full_key_once_and_can_be_dismissed(app):
    app.sign_in()
    app.nav("API Keys")
    page = app.page

    page.get_by_role("button", name=re.compile("generate first key", re.I)).click()
    page.get_by_placeholder(re.compile("production_orchestrator", re.I)).fill("Test Key")
    page.get_by_role("button", name=re.compile("^generate$", re.I)).click()

    # The full raw key is only ever shown here, right after creation.
    full_key = page.get_by_text(re.compile(r"^dv_[0-9a-f]{48}$"))
    full_key.wait_for(state="visible")

    page.get_by_role("button", name=re.compile("dismiss", re.I)).click()
    assert full_key.count() == 0
    # The masked row is unaffected by dismissing the one-time banner.
    page.get_by_text(re.compile(r"^dv_[0-9a-f]{8}•{16}$")).wait_for(state="visible")


@pytest.mark.regression
def test_copy_key_shows_temporary_confirmation(app):
    app.sign_in()
    app.page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    _generate_key(app)
    page = app.page

    page.get_by_role("button", name="Copy", exact=True).click()
    page.get_by_role("button", name="Copied", exact=True).wait_for(state="visible")


@pytest.mark.regression
def test_revoke_requires_confirmation(app):
    app.sign_in()
    _generate_key(app)
    page = app.page
    row = page.locator("tbody tr").first

    page.once("dialog", lambda dialog: dialog.dismiss())
    row.get_by_role("button", name=re.compile("revoke", re.I)).click()
    row.get_by_text("Test Key").wait_for(state="visible")  # unrevoked, still there

    page.once("dialog", lambda dialog: dialog.accept())
    row.get_by_role("button", name=re.compile("revoke", re.I)).click()
    # Revoked keys stay in the table (for audit purposes) but lose their
    # Revoke action and show a "Revoked" status instead.
    row.get_by_text("Revoked", exact=True).wait_for(state="visible")
    assert row.get_by_role("button", name=re.compile("revoke", re.I)).count() == 0


@pytest.mark.smoke
def test_language_tabs_switch_code_snippet(app):
    app.sign_in()
    page = app.page
    app.nav("API Keys")

    page.get_by_role("button", name=re.compile("^python$", re.I)).click()
    page.get_by_text("import requests").wait_for(state="visible")

    page.get_by_role("button", name=re.compile(r"^node\.js$", re.I)).click()
    page.get_by_text("new EventSource").wait_for(state="visible")


@pytest.mark.regression
def test_copy_snippet_is_independent_of_key_copy_state(app):
    """Both copy affordances reset via a real 2s setTimeout. Asserting
    persistence against real wall-clock time is exactly the kind of test
    that's fine on a quiet machine but flakes under `-n auto` once several
    browsers are contending for CPU and a few Playwright round trips eat
    into that 2s budget. Installing Playwright's fake clock makes the two
    independent timers deterministic instead of racing real time."""
    app.sign_in()
    app.page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    _generate_key(app)
    page = app.page

    page.clock.install()

    page.get_by_role("button", name="Copy", exact=True).click()
    page.get_by_role("button", name="Copied", exact=True).wait_for(state="visible")

    snippet_copy_button = page.get_by_title("Copy", exact=True)
    snippet_copy_button.click()
    # The snippet button swaps its lucide Copy icon for a Check icon rather
    # than rendering any text -- select by the icon's class instead.
    snippet_copy_button.locator("svg.lucide-check").wait_for(state="visible")
    # No fake time has elapsed yet -- the banner's own copy confirmation must
    # still be showing, independent of the snippet's copy state.
    assert page.get_by_role("button", name="Copied", exact=True).is_visible()

    # Advancing past the 2s window proves the reset actually fires too.
    page.clock.run_for(2100)
    page.get_by_role("button", name="Copy", exact=True).wait_for(state="visible")
    snippet_copy_button.locator("svg.lucide-copy").wait_for(state="visible")
