import asyncio
from pathlib import Path
from crewai.project import load_crew
from crewai import Memory


memory = Memory(storage='./memory')


async def main(prompt: str) -> dict:
    crew, _ = load_crew(Path(__file__).with_name('crew.jsonc'))
    kickoff = await crew.kickoff_async(inputs={'prompt': prompt})
    response = kickoff.pydantic.model_dump()
    memory.remember(response['response'])
    return response


if __name__ == '__main__':
    print(asyncio.run(main('but what word i called you?')))
