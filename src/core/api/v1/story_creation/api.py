import re
from fastapi import APIRouter, FastAPI
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from core.ai.skill_agent.main import run_character_creator
from core.api.v1.story_creation.schemas import StoryCreationSchema
from core.useful.log import Logger
from typing import AsyncGenerator
from core.settings import Config


log = Logger(name='skill_agent-creation-api')

_FRONTMATTER_RE = re.compile(r'^---\n(.*?)\n---\n(.*)$', re.DOTALL)
_DESCRIPTION_RE = re.compile(r'^description:\s*(.+)$', re.MULTILINE)


def _split_generated_skill(content: str) -> tuple[str, str]:
    match = _FRONTMATTER_RE.match(content)
    if not match:
        return '', content.strip()
    frontmatter, body = match.groups()
    desc_match = _DESCRIPTION_RE.search(frontmatter)
    description = desc_match.group(1).strip() if desc_match else ''
    return description, body.strip()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    log.fire.info(f'{log.name} started successfully')
    yield
    log.fire.info(f'{log.name} stopped successfully')


router = APIRouter(prefix=f'/api/{Config.API_VERSION}/character')


@router.post('/create', response_model=StoryCreationSchema)
async def create_story(query: str, npc_name: str) -> JSONResponse:
    try:
        dest = await run_character_creator(prompt=query, npc_name=npc_name)
        description, persona = _split_generated_skill(dest.read_text(encoding='utf-8'))
        response = JSONResponse({
            'success': True,
            'file_location': str(dest),
            'description': description,
            'persona': persona,
        })
        log.fire.info(f'{response}')
        return response
    except Exception as e:
        log.fire.error(f'{log.name} failed due to exception {e}')
        return JSONResponse({
            'success': False, 'file_location': '', 'description': '', 'persona': '', 'error': str(e),
        })
