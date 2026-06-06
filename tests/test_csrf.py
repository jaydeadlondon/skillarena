from app.core.csrf import CSRF_FORM_FIELD, csrf_input


class FakeRequest:
    def __init__(self):
        self.session = {}


def test_csrf_input_creates_session_token():
    request = FakeRequest()
    html = csrf_input(request)
    assert CSRF_FORM_FIELD in html
    assert "csrf_token" in request.session
    assert request.session["csrf_token"]


def test_csrf_input_reuses_session_token():
    request = FakeRequest()
    first = csrf_input(request)
    second = csrf_input(request)
    assert first == second
