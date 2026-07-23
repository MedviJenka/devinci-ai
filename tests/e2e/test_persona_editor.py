import re

import pytest

pytestmark = pytest.mark.e2e


def _goal_input(page):
    return page.get_by_text("Goal", exact=True).locator("xpath=following-sibling::input")


def _open_persona(app, row: int = 0):
    page = app.page
    app.nav("NPCs")
    page.get_by_title("Edit persona").nth(row).click()
    _goal_input(page).wait_for(state="visible")


@pytest.mark.smoke
def test_save_persona_persists_and_shows_confirmation(app):
    app.npc_api.seed(
        slug="aldric",
        role="Aldric the Smith",
        goal="old goal",
        backstory="old skill_agent",
        llm="gpt-4o",
        persona_notes="old notes",
    )
    app.sign_in()
    page = app.page
    _open_persona(app)

    _goal_input(page).fill("protect the new forge")
    page.get_by_role("button", name=re.compile("save changes", re.I)).click()

    page.get_by_text("Saved", exact=True).wait_for(state="visible")
    assert app.npc_api.npcs["aldric"]["goal"] == "protect the new forge"


@pytest.mark.regression
def test_unsaved_edits_are_lost_when_switching_tabs_away_and_back(app):
    """PersonaEditor keys its local state off the `npc` prop, but the tab
    switch in App unmounts the whole component (it's inside a ternary, not
    just hidden) rather than keeping it alive -- so unsaved edits do not
    survive a round trip through the Chat tab. Documenting the actual
    behavior here rather than assuming persistence."""
    app.npc_api.seed(slug="aldric", role="Aldric the Smith", goal="old goal")
    app.sign_in()
    page = app.page
    _open_persona(app)

    _goal_input(page).fill("new goal, unsaved")

    page.get_by_role("button", name=re.compile("^chat$", re.I)).click()
    page.get_by_role("button", name=re.compile("^persona$", re.I)).click()

    assert _goal_input(page).input_value() == "old goal"


@pytest.mark.edge_case
def test_switching_to_a_different_npc_resets_fields(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith", goal="aldric goal")
    app.npc_api.seed(slug="mira", role="Mira the Scout", goal="mira goal")
    app.sign_in()
    page = app.page

    _open_persona(app, row=0)
    assert _goal_input(page).input_value() == "aldric goal"

    page.get_by_title("Back to library").click()
    _open_persona(app, row=1)
    assert _goal_input(page).input_value() == "mira goal"
