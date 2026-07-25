from openai import AsyncOpenAI
from core.useful.log import Logger
from core.settings import Config
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, FastAPI
from fastapi.responses import StreamingResponse
from core.useful.auth import get_current_user_id
from core.voice.engine import VoiceEngine
from core.voice.schemas import SpeakRequest, VoiceOptions


log = Logger(name='voice-service')

_openai_client = AsyncOpenAI(api_key=Config.OPENAI_API_KEY)


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    log.fire.info(f'{log.name} started successfully')
    yield
    log.fire.info(f'{log.name} stopped successfully')


router = APIRouter(prefix=f'/api/{Config.API_VERSION}/voice', lifespan=lifespan)


@router.get('/options')
async def voice_options_route() -> VoiceOptions:
    return VoiceOptions()


@router.post('/speak')
async def speak_route(req: SpeakRequest, user_id: str = Depends(get_current_user_id)) -> StreamingResponse:
    engine = VoiceEngine(voice=req.voice.value)
    return StreamingResponse(
        engine.stream_bytes(req.text, req.language, _openai_client),
        media_type='audio/mpeg',
    )
