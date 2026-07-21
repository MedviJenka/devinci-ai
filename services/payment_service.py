import uvicorn
from fastapi import FastAPI
from typing import AsyncGenerator
from core.useful.log import Logger
from contextlib import asynccontextmanager
from fastapi.middleware.cors import CORSMiddleware
from core.api.v1.payment.api import router as payment_router


log = Logger(name="payment-service")


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

app.include_router(payment_router)


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=5556)
