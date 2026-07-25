import re
import pytest

pytestmark = pytest.mark.e2e


@pytest.mark.smoke
def test_library_empty_state_creates_first_npc(app):
    app.sign_in()
    page = app.page
    app.nav("NPCs")

    page.get_by_text("The Archive is Silent").wait_for(state="visible")
    page.get_by_role("button", name=re.compile("create new npc", re.I)).click()

    page.get_by_placeholder(re.compile("aldric", re.I)).fill("Aldric the Smith")
    page.get_by_role("button", name=re.compile("^create$", re.I)).click()

    page.get_by_text("Aldric the Smith").wait_for(state="visible")
    assert "aldric-the-smith" in app.npc_api.npcs


@pytest.mark.regression
def test_library_search_filters_by_role_slug_or_goal(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith", goal="protect the forge")
    app.npc_api.seed(slug="mira", role="Mira the Scout", goal="map the ruins")
    app.sign_in()
    page = app.page
    app.nav("NPCs")

    page.get_by_placeholder(re.compile("search by role", re.I)).fill("scout")
    page.get_by_text("Mira the Scout").wait_for(state="visible")
    assert page.get_by_text("Aldric the Smith").count() == 0

    page.get_by_placeholder(re.compile("search by role", re.I)).fill("")
    page.get_by_text("Aldric the Smith").wait_for(state="visible")


@pytest.mark.edge_case
def test_library_search_no_matches(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith")
    app.sign_in()
    page = app.page
    app.nav("NPCs")

    page.get_by_placeholder(re.compile("search by role", re.I)).fill("nonexistent-xyz")
    page.get_by_text("No matches found").wait_for(state="visible")


@pytest.mark.smoke
def test_opening_chat_from_library_row_shows_detail_header(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith", llm="gpt-4o")
    app.sign_in()
    page = app.page
    app.nav("NPCs")

    page.get_by_text("Aldric the Smith").click()
    page.get_by_text("gpt-4o").wait_for(state="visible")
    page.get_by_placeholder(re.compile("say something", re.I)).wait_for(state="visible")


@pytest.mark.smoke
def test_opening_persona_from_library_edit_icon(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith", goal="protect the forge")
    app.sign_in()
    page = app.page
    app.nav("NPCs")

    page.get_by_title("Edit persona").click()
    # `goal` renders inside an <input value=...>, which get_by_text can't
    # see (it isn't a text node) -- asserting on input_value() instead of
    # racing against the outgoing Library row's own goal <p>, which is
    # visible for a brief moment after the click and made this pass for the
    # wrong reason under low load, then time out under parallel load once
    # the race consistently lost.
    goal_input = page.get_by_text("Goal", exact=True).locator("xpath=following-sibling::input")
    goal_input.wait_for(state="visible")
    assert goal_input.input_value() == "protect the forge"
    # Edit icon opens the persona tab, not chat -- no chat input should be present.
    assert page.get_by_placeholder(re.compile("say something", re.I)).count() == 0


@pytest.mark.regression
def test_delete_npc_requires_confirmation(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith")
    app.sign_in()
    page = app.page
    app.nav("NPCs")

    # Deletion is confirmed via an in-app modal (ConfirmDialog), not a native
    # browser dialog.
    page.get_by_title("Delete NPC").click()
    page.get_by_role("button", name=re.compile("^cancel$", re.I)).click()
    page.get_by_text("Aldric the Smith").wait_for(state="visible")  # still there, dismissed

    page.get_by_title("Delete NPC").click()
    page.get_by_role("button", name=re.compile("^delete$", re.I)).click()
    page.get_by_text("The Archive is Silent").wait_for(state="visible")
    assert "aldric" not in app.npc_api.npcs


@pytest.mark.smoke
def test_dashboard_shows_llm_breakdown(app):
    app.npc_api.seed(slug="a", role="A the First", llm="gpt-4o")
    app.npc_api.seed(slug="b", role="B the Second", llm="gpt-4o")
    app.npc_api.seed(slug="c", role="C the Third", llm="claude-3")
    app.sign_in()
    page = app.page
    app.nav("Dashboard")

    page.get_by_text("2 npcs").wait_for(state="visible")
    # Not exact=True: the count and "· NN%" share one text node, e.g. "1 npc · 33%".
    page.get_by_text("1 npc ·").wait_for(state="visible")


@pytest.mark.smoke
def test_dashboard_empty_state_creates_first_npc(app):
    app.sign_in()
    page = app.page
    app.nav("Dashboard")

    page.get_by_text("The Archive is Silent").wait_for(state="visible")
    page.get_by_role("button", name=re.compile("create first npc", re.I)).click()
    page.get_by_placeholder(re.compile("aldric", re.I)).wait_for(state="visible")


@pytest.mark.regression
def test_dashboard_roster_opens_chat(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith", llm="gpt-4o")
    app.sign_in()
    page = app.page
    app.nav("Dashboard")

    page.get_by_text("Aldric the Smith").click()
    page.get_by_placeholder(re.compile("say something", re.I)).wait_for(state="visible")
