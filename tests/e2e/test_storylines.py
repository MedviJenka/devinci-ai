import re

import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.smoke
def test_new_storyline_disabled_without_npcs(app):
    app.sign_in()
    page = app.page
    app.nav("Storylines")

    page.get_by_text("Create an NPC first").wait_for(state="visible")
    new_storyline_button = page.get_by_role("button").filter(has_text=re.compile("new storyline", re.I))
    assert new_storyline_button.is_disabled()


@pytest.mark.smoke
def test_create_and_delete_storyline_draft(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith")
    app.sign_in()
    page = app.page
    app.nav("Storylines")

    page.get_by_role("button", name=re.compile("draft first storyline", re.I)).click()
    page.get_by_placeholder(re.compile("lost apprentice", re.I)).fill("The Missing Ledger")
    page.get_by_role("button", name=re.compile("save draft", re.I)).click()

    page.get_by_text("The Missing Ledger").wait_for(state="visible")
    page.get_by_text("Aldric the Smith").wait_for(state="visible")

    page.get_by_title("Delete draft").click()
    assert page.get_by_text("The Missing Ledger").count() == 0


@pytest.mark.edge_case
def test_storylines_state_does_not_survive_navigating_away(app):
    """Storylines is only mounted while `screen === 'storylines'` -- App.tsx
    renders it inside a conditional (`{screen === 'storylines' && <Storylines
    .../>}`), not just hidden -- so its local `storylines` useState is
    discarded on any navigation away and rebuilt empty on return. There's no
    persistence layer backing drafts yet. Confirmed by running this against
    the real app rather than assumed: a draft created here does not survive
    a round trip to another screen and back."""
    app.npc_api.seed(slug="aldric", role="Aldric the Smith")
    app.sign_in()
    page = app.page
    app.nav("Storylines")

    page.get_by_role("button", name=re.compile("draft first storyline", re.I)).click()
    page.get_by_placeholder(re.compile("lost apprentice", re.I)).fill("The Missing Ledger")
    page.get_by_role("button", name=re.compile("save draft", re.I)).click()
    page.get_by_text("The Missing Ledger").wait_for(state="visible")

    app.nav("NPCs")
    app.nav("Storylines")

    assert page.get_by_text("The Missing Ledger").count() == 0
    page.get_by_text("Draft your first narrative arc").wait_for(state="visible")
