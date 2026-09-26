import re
from pathlib import Path

from core.settings import Config


def slugify(name: str) -> str:
    slug = re.sub(r'[^a-z0-9]+', '_', name.strip().lower()).strip('_')
    if not slug:
        raise ValueError('name must contain at least one alphanumeric character')
    return slug


def _bucket() -> str:
    return Config.NPC_STORAGE_BUCKET


def _user_prefix(user_id: str) -> str:
    return f'{user_id}/'


def _npc_prefix(user_id: str, slug: str) -> str:
    return f'{user_id}/{slug}/'


def _cache_dir(user_id: str, slug: str) -> Path:
    return Path(Config.NPC_CACHE_DIR) / user_id / slug
