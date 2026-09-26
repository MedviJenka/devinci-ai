from fastapi import HTTPException, Query, Request
from supabase_auth.errors import AuthError

from core.database.api_keys.client import KEY_PREFIX, ApiKeys
from core.settings import db

_api_keys = ApiKeys()


def _extract_token(request: Request, token: str | None) -> str:
    auth_header = request.headers.get('authorization')
    if auth_header and auth_header.lower().startswith('bearer '):
        return auth_header[len('bearer '):].strip()
    if token:
        return token
    raise HTTPException(status_code=401, detail='missing bearer token')


def get_current_user_id(request: Request, token: str | None = Query(default=None)) -> str:
    raw = _extract_token(request, token)

    # Long-lived API keys (e.g. for non-browser clients like the pygame game) skip
    # Supabase session validation entirely and resolve straight to a user_id.
    if raw.startswith(KEY_PREFIX):
        user_id = _api_keys.resolve(raw)
        if user_id is None:
            raise HTTPException(status_code=401, detail='invalid or revoked api key')
        return user_id

    try:
        response = db.auth.get_user(raw)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail='invalid or expired token') from exc

    if response is None or response.user is None:
        raise HTTPException(status_code=401, detail='invalid or expired token')

    return response.user.id
