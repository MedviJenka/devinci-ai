from core.useful.log import Logger
from core.settings import Config
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import APIRouter, FastAPI
from core.voice.schemas import VoiceOptions


log = Logger(name='voice-service')


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    log.fire.info(f'{log.name} started successfully')
    yield
    log.fire.info(f'{log.name} stopped successfully')


router = APIRouter(prefix=f'/api/{Config.API_VERSION}/voice', lifespan=lifespan)


@router.get('/options')
async def voice_options_route() -> VoiceOptions:
    return VoiceOptions()
