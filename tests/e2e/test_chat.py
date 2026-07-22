import re
import pytest

pytestmark = pytest.mark.e2e


def _open_chat(app, slug: str, role: str):
    page = app.page
    app.nav("NPCs")
    page.get_by_text(role).click()
    page.get_by_placeholder(re.compile("say something", re.I)).wait_for(state="visible")


@pytest.mark.smoke
def test_send_message_shows_player_bubble_and_streamed_reply(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith")
    app.sign_in()
    _open_chat(app, "aldric", "Aldric the Smith")
    page = app.page

    page.get_by_placeholder(re.compile("say something", re.I)).fill("hello there")
    page.keyboard.press("Enter")

    # exact=True: once the npc reply "Echo: hello there" streams in, a
    # substring match on "hello there" ambiguously matches both bubbles.
    page.get_by_text("hello there", exact=True).wait_for(state="visible")
    page.get_by_text(re.compile("echo: hello there", re.I)).wait_for(state="visible")
    page.get_by_text("neutral").wait_for(state="visible")

    assert app.npc_api.talk_requests == [("aldric", "hello there")]


@pytest.mark.edge_case
def test_send_button_disabled_for_blank_input(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith")
    app.sign_in()
    _open_chat(app, "aldric", "Aldric the Smith")
    page = app.page

    send_button = page.get_by_role("button", name="send", exact=True)
    assert send_button.is_disabled()

    page.get_by_placeholder(re.compile("say something", re.I)).fill("   ")
    assert send_button.is_disabled()


@pytest.mark.regression
def test_streaming_error_renders_as_npc_message(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith")
    app.npc_api.stream_events = [{"type": "error", "message": "Connection lost."}]
    app.sign_in()
    _open_chat(app, "aldric", "Aldric the Smith")
    page = app.page

    page.get_by_placeholder(re.compile("say something", re.I)).fill("hello")
    page.keyboard.press("Enter")

    page.get_by_text("Connection lost.").wait_for(state="visible")
    # Input re-enables after the error resolves `pending`.
    send_button = page.get_by_role("button", name="send", exact=True)
    page.get_by_placeholder(re.compile("say something", re.I)).fill("again")
    assert not send_button.is_disabled()


@pytest.mark.regression
def test_switching_npc_clears_chat_history(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith")
    app.npc_api.seed(slug="mira", role="Mira the Scout")
    app.sign_in()
    page = app.page

    _open_chat(app, "aldric", "Aldric the Smith")
    page.get_by_placeholder(re.compile("say something", re.I)).fill("hello aldric")
    page.keyboard.press("Enter")
    page.get_by_text(re.compile("echo: hello aldric", re.I)).wait_for(state="visible")

    page.get_by_title("Back to library").click()
    _open_chat(app, "mira", "Mira the Scout")

    assert page.get_by_text("hello aldric").count() == 0
    page.get_by_text("NPC Sequence Initiated").wait_for(state="visible")
