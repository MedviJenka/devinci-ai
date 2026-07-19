import uvicorn
from log import Logger
from settings import Config
from stream import _sse
from assets.src.npc.crew import Npc
from fastapi import FastAPI, Query
from typing import AsyncGenerator
from contextlib import asynccontextmanager
from fastapi.responses import StreamingResponse


log = Logger(name="api-service")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    log.fire.info(f'{log.name} started successfully')
    yield
    log.fire.info(f'{log.name} finished successfully')


app = FastAPI(lifespan=lifespan)


@app.get(f'/api/{Config.API_VERSION}/npc/name')
async def talk_stream(query: str = Query(default=..., description='player query')) -> StreamingResponse:
    
    async def generate() -> AsyncGenerator:
        try:
            streaming = await Npc().crew().kickoff_async(inputs={'query': query})

            chunks: list[str] = []

            async for chunk in streaming:
                chunks.append(chunk.content)

            final_text = streaming.result.raw
            full = ''.join(chunks)
            start = full.find(final_text)

            if start >= 0:
                offset = 0
                for text in chunks:
                    end = offset + len(text)
                    if end > start:
                        trimmed = text[max(0, start - offset):]
                        if trimmed:
                            yield _sse({'type': 'chunk', 'text': trimmed})
                    offset = end
            else:
                yield _sse({'type': 'chunk', 'text': final_text})

            yield _sse({'type': 'done', 'text': final_text})
        except Exception as exc:
            log.fire.error(f'stream failed: {exc}')
            yield _sse({'type': 'error', 'message': 'Failed to generate response.'})

    return StreamingResponse(
        generate(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )


if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=5555)
