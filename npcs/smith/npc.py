import asyncio
from pathlib import Path
import core.ai.crewai_compat  # noqa: F401
from crewai.project import load_crew
from crewai.types.streaming import CrewStreamingOutput


async def main(prompt: str) -> CrewStreamingOutput:
    crew, _ = load_crew(Path(__file__).with_name('crew.jsonc'))
    return await crew.kickoff_async(inputs={'prompt': prompt})


async def _demo() -> None:
    streaming = await main('hello')
    async for chunk in streaming:
        print(chunk.content, end='')
    print()
    print(streaming.result.pydantic)


if __name__ == '__main__':
    asyncio.run(_demo())
