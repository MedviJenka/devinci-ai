from fastapi import HTTPException, Query, Request
from supabase_auth.errors import AuthError

from core.settings import db


def _extract_token(request: Request, token: str | None) -> str:
    auth_header = request.headers.get('authorization')
    if auth_header and auth_header.lower().startswith('bearer '):
        return auth_header[len('bearer '):].strip()
    if token:
        return token
    raise HTTPException(status_code=401, detail='missing bearer token')


def get_current_user_id(request: Request, token: str | None = Query(default=None)) -> str:
    jwt = _extract_token(request, token)
    try:
        response = db.auth.get_user(jwt)
    except AuthError as exc:
        raise HTTPException(status_code=401, detail='invalid or expired token') from exc

    if response is None or response.user is None:
        raise HTTPException(status_code=401, detail='invalid or expired token')

    return response.user.id
