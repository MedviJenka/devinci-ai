import uvicorn
from core.useful.log import Logger
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from core.api.v1.npcs.api import router as npc_router
from core.api.v1.story_creation.api import router as story_router
from core.api.v1.voice.api import router as voice_router

log = Logger(name="api-service")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    log.fire.info(f'{log.name} started successfully')
    yield
    log.fire.info(f'{log.name} finished successfully')


app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['http://localhost:3000'],
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(npc_router)
app.include_router(story_router)
app.include_router(voice_router)



if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=5555)
