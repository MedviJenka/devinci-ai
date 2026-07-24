import json
import posixpath
import re
from typing import Any
from core.storage import client as storage
from core.npc_manager.paths import bucket, cache_dir, npc_prefix
from core.npc_manager.schemas import PydanticFieldDef
from core.npc_manager.templates import LEGACY_FILES, SKILL_MD, STRICT_RULES
from core.npc_manager.validation import validate_pydantic_fields


def _render_npc_config(
    role: str, goal: str, backstory: str, llm: str, enabled: bool, fields: list[PydanticFieldDef],
) -> str:
    return json.dumps({
        'role': role,
        'goal': goal,
        'backstory': backstory,
        'llm': llm,
        'pydantic_enabled': enabled,
        'pydantic_fields': [field.model_dump() for field in fields],
    }, indent=2)


def parse_npc_config(text: str) -> dict[str, Any]:
    data = json.loads(text)
    data['pydantic_fields'] = [PydanticFieldDef(**field) for field in data['pydantic_fields']]
    return data


def skill_md_key(user_id: str, slug: str) -> str | None:
    prefix = npc_prefix(user_id, slug) + 'skills/'
    for key in storage.list_files(bucket(), prefix):
        if key.endswith('/SKILL.md'):
            return key
    return None


def split_skill_md(text: str) -> tuple[str, str]:
    match = re.match(r'^---\n(.*?)\n---\n(.*)$', text, flags=re.DOTALL)
    if not match:
        return '', text
    frontmatter, body = match.groups()
    description = ''
    for line in frontmatter.splitlines():
        if line.startswith('description:'):
            description = line.split(':', 1)[1].strip()

    body = body.strip('\n')
    if body.startswith(STRICT_RULES):
        body = body[len(STRICT_RULES):].strip('\n')
    return description, body


def write_file(user_id: str, slug: str, rel_path: str, content: str) -> None:
    local_path = cache_dir(user_id, slug) / rel_path
    local_path.parent.mkdir(parents=True, exist_ok=True)
    local_path.write_text(content, encoding='utf-8')
    # normalize away '..' segments (e.g. rel_path='../__init__.py'): Supabase Storage's
    # Cloudflare front collapses '..' in the URL path before it reaches the S3-compatible
    # origin, which no longer matches the path boto3 signed -> SignatureDoesNotMatch.
    storage_key = posixpath.normpath(npc_prefix(user_id, slug) + rel_path)
    storage.put_text(bucket(), storage_key, content)


def write_npc_config(
    user_id: str, slug: str, goal: str, backstory: str, llm: str, enabled: bool, fields: list[PydanticFieldDef],
) -> None:
    validate_pydantic_fields(fields)
    if enabled and not fields:
        raise ValueError('at least one field is required when structured output is enabled')
    content = _render_npc_config(role=slug, goal=goal, backstory=backstory, llm=llm, enabled=enabled, fields=fields)
    write_file(user_id, slug, 'npc.json', content)


def write_skill_md(user_id: str, slug: str, skill_dir_name: str, goal: str, persona_notes: str) -> None:
    content = SKILL_MD.format(slug=skill_dir_name, description=goal, persona_notes=persona_notes.strip())
    write_file(user_id, slug, f'skills/{skill_dir_name}/SKILL.md', content)


def prune_legacy_files(user_id: str, slug: str) -> None:
    prefix = npc_prefix(user_id, slug)
    local_cache_dir = cache_dir(user_id, slug)
    for name in LEGACY_FILES:
        key = prefix + name
        if storage.exists(bucket(), key):
            storage.delete(bucket(), key)
        local_path = local_cache_dir / name
        if local_path.exists():
            local_path.unlink()
