"""One-off: assign the pre-tenancy demo NPCs (smith, marcus_holt) to a real user.

These NPCs predate per-user storage and have no owner. Run once after deploying
the tenancy change:

    uv run python -m scripts.migrate_existing_npcs --email you@example.com
"""

import argparse
from pathlib import Path
from core.settings import db
from npcs.manager import NpcCreateRequest, _load_jsonc_text, _split_skill_md, create_npc

OLD_NPCS_DIR = Path(__file__).resolve().parent.parent / 'npcs'
SLUGS = ['smith', 'marcus_holt']


def _find_user_id(email: str) -> str:
    page = 1
    while True:
        users = db.auth.admin.list_users(page=page, per_page=200)
        if not users:
            raise SystemExit(f'no user found with email {email!r}')
        for user in users:
            if user.email == email:
                return user.id
        page += 1


def _migrate_one(user_id: str, slug: str) -> None:
    npc_dir = OLD_NPCS_DIR / slug
    crew = _load_jsonc_text((npc_dir / 'crew.jsonc').read_text(encoding='utf-8'))
    agent_name = crew['agents'][0]
    agent = _load_jsonc_text((npc_dir / 'agents' / f'{agent_name}.jsonc').read_text(encoding='utf-8'))

    skill_path = next((npc_dir / 'skills').glob('*/SKILL.md'), None)
    persona_notes = _split_skill_md(skill_path.read_text(encoding='utf-8'))[1] if skill_path else ''

    req = NpcCreateRequest(
        name=slug,
        goal=agent['goal'],
        backstory=agent.get('backstory', ''),
        llm=agent['llm'],
        persona_notes=persona_notes,
    )
    created = create_npc(user_id, req)
    print(f'migrated {slug!r} -> owned by {user_id} (role={created.role!r})')


def main() -> None:
    parser = argparse.ArgumentParser(description='Assign the existing ownerless demo NPCs to a Supabase user.')
    parser.add_argument('--email', required=True, help='Supabase auth user email to assign the NPCs to')
    args = parser.parse_args()

    user_id = _find_user_id(args.email)

    for slug in SLUGS:
        _migrate_one(user_id, slug)


if __name__ == '__main__':
    main()
