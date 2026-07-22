import hashlib
import secrets
from dataclasses import dataclass
from datetime import datetime, timezone

from core.database.api_keys.schemas import ApiKeyCreateResponse, ApiKeySummary
from core.settings import db

KEY_PREFIX = 'dv_'
_DISPLAY_PREFIX_LEN = len(KEY_PREFIX) + 8

_SUMMARY_COLUMNS = 'id, name, key_prefix, created_at, last_used_at, revoked_at'


class ApiKeyNotFoundError(Exception):
    pass


def _hash(raw_key: str) -> str:
    return hashlib.sha256(raw_key.encode()).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ApiKeys:

    def __post_init__(self) -> None:
        self.db = db

    def create(self, user_id: str, name: str) -> ApiKeyCreateResponse:
        raw_key = f'{KEY_PREFIX}{secrets.token_hex(24)}'
        row = {
            'user_id': user_id,
            'name': name,
            'key_hash': _hash(raw_key),
            'key_prefix': raw_key[:_DISPLAY_PREFIX_LEN],
        }
        response = self.db.table('api_keys').insert(row).execute()
        return ApiKeyCreateResponse(key=raw_key, **response.data[0])

    def list(self, user_id: str) -> list[ApiKeySummary]:
        response = (
            self.db.table('api_keys')
            .select(_SUMMARY_COLUMNS)
            .eq('user_id', user_id)
            .order('created_at', desc=True)
            .execute()
        )
        return [ApiKeySummary(**row) for row in response.data]

    def revoke(self, user_id: str, key_id: str) -> None:
        response = (
            self.db.table('api_keys')
            .update({'revoked_at': _now()})
            .eq('id', key_id)
            .eq('user_id', user_id)
            .execute()
        )
        if not response.data:
            raise ApiKeyNotFoundError(key_id)

    def resolve(self, raw_key: str) -> str | None:
        """Look up the user_id a raw API key belongs to, or None if it's unknown/revoked."""
        response = (
            self.db.table('api_keys')
            .select('id, user_id, revoked_at')
            .eq('key_hash', _hash(raw_key))
            .maybe_single()
            .execute()
        )
        if not response or not response.data or response.data['revoked_at'] is not None:
            return None

        row = response.data
        self.db.table('api_keys').update({'last_used_at': _now()}).eq('id', row['id']).execute()
        return row['user_id']
