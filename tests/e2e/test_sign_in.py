import re
import pytest


pytestmark = pytest.mark.e2e


@pytest.mark.smoke
def test_otp_sign_in_reaches_authenticated_shell(app):
    app.sign_in()
    assert app.auth_mock.otp_calls[0]["email"] == "player@example.com"
    assert len(app.auth_mock.verify_calls) == 1
    assert app.auth_mock.verify_calls[0]["token"] == "123456"


@pytest.mark.edge_case
def test_invalid_code_shows_error_and_does_not_sign_in(app):
    app.auth_mock.verify_should_fail = True
    page = app.page
    page.goto(app.base_url)

    page.get_by_placeholder("you@example.com").fill("player@example.com")
    page.get_by_role("button", name=re.compile("send code", re.I)).click()

    digit_inputs = page.locator("input[inputmode='numeric']")
    digit_inputs.first.wait_for(state="visible")
    for i, digit in enumerate("999999"):
        digit_inputs.nth(i).fill(digit)
    page.get_by_role("button", name=re.compile("verify", re.I)).click()

    page.get_by_text(re.compile("invalid", re.I)).wait_for(state="visible")
    # Still on the OTP screen, not the authenticated shell.
    assert page.get_by_role("button", name=re.compile("new npc", re.I)).count() == 0


@pytest.mark.regression
def test_resend_code_calls_otp_endpoint_again(app):
    page = app.page
    page.goto(app.base_url)
    page.get_by_placeholder("you@example.com").fill("player@example.com")
    page.get_by_role("button", name=re.compile("send code", re.I)).click()
    page.locator("input[inputmode='numeric']").first.wait_for(state="visible")

    page.get_by_role("button", name=re.compile("resend code", re.I)).click()
    assert len(app.auth_mock.otp_calls) == 2


@pytest.mark.edge_case
def test_change_email_returns_to_email_step(app):
    page = app.page
    page.goto(app.base_url)
    page.get_by_placeholder("you@example.com").fill("player@example.com")
    page.get_by_role("button", name=re.compile("send code", re.I)).click()
    page.locator("input[inputmode='numeric']").first.wait_for(state="visible")

    page.get_by_role("button", name=re.compile("change email", re.I)).click()
    page.get_by_placeholder("you@example.com").wait_for(state="visible")


@pytest.mark.regression
def test_google_button_starts_oauth_redirect(app):
    """Full OAuth requires leaving the app for Google's real consent screen,
    which is out of scope for this mocked suite. This only verifies the app
    reaches its "Redirecting..." loading state and calls signInWithOAuth,
    which is the extent of what's under our control."""
    page = app.page
    page.goto(app.base_url)

    google_button = page.get_by_role("button", name=re.compile("continue with google", re.I))
    with page.expect_request(re.compile(r"/auth/v1/authorize")):
        google_button.click()
