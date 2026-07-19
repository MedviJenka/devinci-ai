import uvicorn
from core.log import Logger
from core.settings import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from npc_routes import router as npc_router


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

app.include_router(npc_router, prefix=f'/api/{Config.API_VERSION}/npcs')


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=5555)
