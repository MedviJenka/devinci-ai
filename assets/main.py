import asyncio
from pathlib import Path
from crewai.project import load_crew


async def main(prompt: str) -> str:
    crew, _ = load_crew(Path(__file__).with_name('crew.jsonc'))
    response = await crew.kickoff_async(inputs={'prompt': prompt})
    return response.raw


if __name__ == '__main__':
    print(asyncio.run(main('where did you born?')))
