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
    app.npc_api.seed(slug="aldric", role="Aldric the Smith", pydantic_enabled=True)
    app.sign_in()
    _open_chat(app, "aldric", "Aldric the Smith")
    page = app.page

    page.get_by_placeholder(re.compile("say something", re.I)).fill("hello there")
    page.keyboard.press("Enter")

    # exact=True: once the npc reply "Echo: hello there" streams in, a
    # substring match on "hello there" ambiguously matches both bubbles.
    page.get_by_text("hello there", exact=True).wait_for(state="visible")
    page.get_by_text(re.compile("echo: hello there", re.I)).wait_for(state="visible")
    page.get_by_text("neutral", exact=True).wait_for(state="visible")

    assert app.npc_api.talk_requests == [("aldric", "hello there")]


@pytest.mark.edge_case
def test_send_button_disabled_for_blank_input(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith")
    app.sign_in()
    _open_chat(app, "aldric", "Aldric the Smith")
    page = app.page

    send_button = page.get_by_role("button", name=re.compile("^send$", re.I))
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
    send_button = page.get_by_role("button", name=re.compile("^send$", re.I))
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


@pytest.mark.regression
def test_plain_text_npc_reply_is_shown_as_dialogue(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith")
    app.sign_in()
    _open_chat(app, "aldric", "Aldric the Smith")
    page = app.page

    page.get_by_placeholder(re.compile("say something", re.I)).fill("hello there")
    page.keyboard.press("Enter")

    page.get_by_text("Echo: hello there", exact=True).wait_for(state="visible")


@pytest.mark.regression
def test_remembered_conversation_is_shown_when_chat_opens(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith")
    app.npc_api.history["aldric"] = [
        {"ts": "2026-10-27T10:00:00+00:00", "query": "my name is Mira", "response": "Hmph. Mira, is it."},
    ]
    app.sign_in()
    _open_chat(app, "aldric", "Aldric the Smith")
    page = app.page

    page.get_by_text("my name is Mira", exact=True).wait_for(state="visible")
    page.get_by_text("Hmph. Mira, is it.", exact=True).wait_for(state="visible")
    page.get_by_text("Remembered conversation").wait_for(state="visible")

    # New turns continue below the remembered ones.
    page.get_by_placeholder(re.compile("say something", re.I)).fill("remember me?")
    page.keyboard.press("Enter")
    page.get_by_text("Echo: remember me?", exact=True).wait_for(state="visible")


@pytest.mark.regression
def test_clearing_memory_removes_remembered_conversation(app):
    app.npc_api.seed(slug="aldric", role="Aldric the Smith")
    app.npc_api.history["aldric"] = [
        {"ts": "2026-10-27T10:00:00+00:00", "query": "my name is Mira", "response": "Hmph. Mira, is it."},
    ]
    app.sign_in()
    _open_chat(app, "aldric", "Aldric the Smith")
    page = app.page
    page.get_by_text("my name is Mira", exact=True).wait_for(state="visible")

    page.get_by_role("button", name=re.compile("^persona$", re.I)).click()
    page.get_by_role("button", name=re.compile("^clear memory$", re.I)).click()
    page.get_by_role("dialog").get_by_role("button", name=re.compile("clear memory", re.I)).click()
    page.get_by_text('Cleared memory for "aldric".').wait_for(state="visible")
    page.get_by_role("button", name=re.compile("^chat$", re.I)).click()

    page.get_by_text("NPC Sequence Initiated").wait_for(state="visible")
    assert page.get_by_text("my name is Mira").count() == 0
    assert app.npc_api.memory_resets == ["aldric"]
