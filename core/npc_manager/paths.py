from pathlib import Path
from core.settings import Config


def bucket() -> str:
    return Config.NPC_STORAGE_BUCKET


def user_prefix(user_id: str) -> str:
    return f'{user_id}/'


def npc_prefix(user_id: str, slug: str) -> str:
    return f'{user_id}/{slug}/'


def cache_dir(user_id: str, slug: str) -> Path:
    return Path(Config.NPC_CACHE_DIR) / user_id / slug
