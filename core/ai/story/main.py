import asyncio
import re
from pathlib import Path
from crewai.project import load_crew

_FRONTMATTER_NAME_RE = re.compile(r'^---\n.*?^name:\s*(\S+)\s*$.*?^---\n', re.DOTALL | re.MULTILINE)


def _slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.strip().lower()).strip('_')


async def run_character_creator(prompt: str, npc_name: str) -> Path:
    crew, _ = load_crew(Path(__file__).with_name('crew.jsonc'))
    await crew.kickoff_async({'prompt': prompt, 'npc_name': npc_name})

    output_path = Path(__file__).with_name('output')/'SKILL.md'
    content = output_path.read_text(encoding='utf-8')

    match = _FRONTMATTER_NAME_RE.match(content)
    skill_name = match.group(1) if match else _slugify(npc_name)

    dest = Path(__file__).with_name('skills')/skill_name/'SKILL.md'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding='utf-8')
    output_path.unlink()

    return dest


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(run_character_creator(prompt='create a story about npc', npc_name='john alberts'))
