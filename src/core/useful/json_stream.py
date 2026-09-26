import json
import re

_RESPONSE_KEY_RE = re.compile(r'"response"\s*:\s*"')


class ResponseFieldStreamer:
    """Incrementally extracts the "response" string value out of a JSON object
    while it's still being streamed token-by-token from the LLM.

    crewAI's structured output (output_pydantic) streams raw JSON text - e.g.
    `{"mood": "Happy", "response": "Well met, traveler."}` - one fragment at a
    time. Waiting for the whole object to finish before showing anything means
    "streaming" buys nothing. This lets the caller push each fragment in and
    get back only the newly available, JSON-decoded slice of the "response"
    value's text so far.
    """

    def __init__(self) -> None:
        self._buffer = ''
        self._emitted = ''

    def feed(self, fragment: str) -> str:
        self._buffer += fragment
        match = _RESPONSE_KEY_RE.search(self._buffer)
        if match is None:
            return ''

        body = self._buffer[match.end():]
        end = _find_unescaped_quote(body)
        value = body[:end] if end is not None else _decodable_prefix(body)
        if not value:
            return ''

        try:
            decoded = json.loads(f'"{value}"')
        except ValueError:
            return ''

        if len(decoded) <= len(self._emitted):
            return ''

        delta = decoded[len(self._emitted):]
        self._emitted = decoded
        return delta

    def remainder(self, complete_text: str) -> str:
        """Catch-up call once the full response text is known (post-stream), in
        case incremental extraction missed a trailing fragment (e.g. the last
        chunk landed mid-escape-sequence)."""
        if len(complete_text) <= len(self._emitted):
            return ''
        delta = complete_text[len(self._emitted):]
        self._emitted = complete_text
        return delta


def _find_unescaped_quote(body: str) -> int | None:
    i = 0
    n = len(body)
    while i < n:
        c = body[i]
        if c == '\\':
            i += 2
            continue
        if c == '"':
            return i
        i += 1
    return None


def _decodable_prefix(body: str) -> str:
    """Trim `body` (an unterminated JSON string's raw contents) back to the
    longest prefix that doesn't end mid-escape-sequence, so it's always safe
    to wrap in quotes and json.loads."""
    trailing_backslashes = 0
    i = len(body) - 1
    while i >= 0 and body[i] == '\\':
        trailing_backslashes += 1
        i -= 1
    if trailing_backslashes % 2 == 1:
        body = body[:-1]
    return re.sub(r'\\u[0-9a-fA-F]{0,3}$', '', body)
