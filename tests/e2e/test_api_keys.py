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
    # maskKey does key.slice(0, 8) on "dv_local_<32 hex>", which yields just
    # "dv_local" (8 chars) -- the underscore is the 9th char and gets cut.
    app.page.get_by_text(re.compile(r"^dv_local•{16}.{4}$")).wait_for(state="visible")


@pytest.mark.regression
def test_reveal_toggle_shows_and_hides_full_key(app):
    app.sign_in()
    _generate_key(app)
    page = app.page
    row = page.locator("tbody tr").first

    row.get_by_title("Reveal").click()
    assert page.get_by_text(re.compile(r"^dv_local_[0-9a-f]{32}$")).count() == 1

    row.get_by_title("Hide").click()
    assert page.get_by_text(re.compile(r"^dv_local_[0-9a-f]{32}$")).count() == 0


@pytest.mark.regression
def test_copy_key_shows_temporary_confirmation(app):
    app.sign_in()
    app.page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    _generate_key(app)
    page = app.page
    row = page.locator("tbody tr").first

    row.get_by_title("Copy").click()
    row.get_by_role("button", name="check", exact=True).wait_for(state="visible")


@pytest.mark.regression
def test_revoke_requires_confirmation(app):
    app.sign_in()
    _generate_key(app)
    page = app.page

    page.once("dialog", lambda dialog: dialog.dismiss())
    page.get_by_role("button", name=re.compile("revoke", re.I)).click()
    page.get_by_text("Test Key").wait_for(state="visible")  # still there

    page.once("dialog", lambda dialog: dialog.accept())
    page.get_by_role("button", name=re.compile("revoke", re.I)).click()
    page.get_by_text("No API keys yet").wait_for(state="visible")


@pytest.mark.smoke
def test_language_tabs_switch_code_snippet(app):
    app.sign_in()
    page = app.page
    app.nav("API Keys")

    page.get_by_role("button", name=re.compile("^python$", re.I)).click()
    page.get_by_text("import requests").wait_for(state="visible")

    page.get_by_role("button", name=re.compile(r"^node\.js$", re.I)).click()
    page.get_by_text("axios.post").wait_for(state="visible")


@pytest.mark.regression
def test_copy_snippet_is_independent_of_key_copy_state(app):
    """Both copy buttons reset their "check" icon via a real 2s setTimeout.
    Asserting persistence against real wall-clock time is exactly the kind
    of test that's fine on a quiet machine but flakes under `-n auto` once
    several browsers are contending for CPU and a few Playwright round trips
    eat into that 2s budget. Installing Playwright's fake clock makes the
    two independent timers deterministic instead of racing real time."""
    app.sign_in()
    app.page.context.grant_permissions(["clipboard-read", "clipboard-write"])
    _generate_key(app)
    page = app.page
    row = page.locator("tbody tr").first

    page.clock.install()

    row.get_by_title("Copy").click()
    row.get_by_role("button", name="check", exact=True).wait_for(state="visible")

    snippet_copy_button = page.get_by_title("Copy", exact=True).nth(1)
    snippet_copy_button.click()
    snippet_copy_button.get_by_text("check", exact=True).wait_for(state="visible")
    # No fake time has elapsed yet -- the row's own copy confirmation must
    # still be showing, independent of the snippet's copy state.
    assert row.get_by_role("button", name="check", exact=True).is_visible()

    # Advancing past the 2s window proves the reset actually fires too.
    page.clock.run_for(2100)
    row.get_by_role("button", name="content_copy", exact=True).wait_for(state="visible")
    snippet_copy_button.get_by_text("content_copy", exact=True).wait_for(state="visible")
