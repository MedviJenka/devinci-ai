from fastapi import APIRouter, FastAPI
from contextlib import asynccontextmanager
from core.api.v1.story_creation.schemas import StoryCreationSchema
from core.log import Logger
from typing import AsyncGenerator
from core.settings import Config


log = Logger(name='story-creation-api')


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    log.fire.info(f'{log.name} started successfully')
    yield
    log.fire.info(f'{log.name} stopped successfully')


router = APIRouter(f'/api/{Config.API_VERSION}/story')


@router.post('/create', response_model=StoryCreationSchema)
async def create_story(query: str, npc_name: str) -> None:
    ...