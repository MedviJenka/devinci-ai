import asyncio
import re
from pathlib import Path
from crewai.project import load_crew

_FRONTMATTER_NAME_RE = re.compile(r'^---\n.*?^name:\s*(\S+)\s*$.*?^---\n', re.DOTALL | re.MULTILINE)


def _slugify(name: str) -> str:
    return re.sub(r'[^a-z0-9]+', '_', name.strip().lower()).strip('_')


async def run_character_creator(prompt: str, npc_name: str) -> Path:
    crew, _ = load_crew(Path(__file__).with_name('crew.jsonc'))
    # crew.jsonc has "stream": true, so kickoff_async() returns a CrewStreamingOutput
    # whose real execution is lazy - it doesn't run until the stream is iterated. Nothing
    # here consumes chunks, so just drain it to drive the crew to completion.
    streaming = await crew.kickoff_async({'prompt': prompt, 'npc_name': npc_name})
    async for _ in streaming:
        pass
    # Read the task's output straight off the result instead of round-tripping through
    # Task's output_file: that path is resolved relative to the process's cwd (not this
    # project directory), and crewAI's own output_file_validation strips a leading "/"
    # from absolute paths as a security guardrail, so there's no reliable on-disk
    # location to read back from.
    content = streaming.result.raw

    match = _FRONTMATTER_NAME_RE.match(content)
    skill_name = match.group(1) if match else _slugify(npc_name)

    dest = Path(__file__).with_name('skills')/skill_name/'SKILL.md'
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding='utf-8')

    return dest


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(run_character_creator(prompt='create a skill_agent about npc', npc_name='john alberts'))
