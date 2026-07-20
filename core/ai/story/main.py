import asyncio
from pathlib import Path
import core.ai.crewai_compat  # noqa: F401
from crewai.project import load_crew


async def run_story_creator(prompt: str, npc_name: str) -> None:
    crew, _ = load_crew(Path(__file__).with_name('crew.jsonc'))
    kickoff = await crew.kickoff({'prompt': prompt, 'npc_name': npc_name})
    return kickoff


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(run_story_creator(prompt='create a story about npc', npc_name='john alberts'))
