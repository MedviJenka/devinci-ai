import importlib
from typing import AsyncGenerator
from core.log import Logger
from core.stream import _sse
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from npcs.manager import (
    NpcAlreadyExistsError,
    NpcCreateRequest,
    NpcDetail,
    NpcNotFoundError,
    NpcSummary,
    NpcUpdateRequest,
    create_npc,
    delete_npc,
    get_npc,
    list_npcs,
    update_npc,
)

log = Logger(name="npc-service")

router = APIRouter()


@router.get('/')
async def list_npcs_route() -> list[NpcSummary]:
    return list_npcs()


@router.post('/', status_code=201)
async def create_npc_route(req: NpcCreateRequest) -> NpcDetail:
    try:
        return create_npc(req)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NpcAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=f'npc "{exc}" already exists') from exc


@router.get('/{slug}')
async def get_npc_route(slug: str) -> NpcDetail:
    try:
        return get_npc(slug)
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc


@router.put('/{slug}')
async def update_npc_route(slug: str, req: NpcUpdateRequest) -> NpcDetail:
    try:
        return update_npc(slug, req)
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc


@router.delete('/{slug}', status_code=204)
async def delete_npc_route(slug: str) -> None:
    try:
        delete_npc(slug)
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc


@router.get('/{slug}/talk')
async def talk_stream(slug: str, query: str = Query(default=..., description='player query')) -> StreamingResponse:
    try:
        get_npc(slug)
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc

    npc_module = importlib.import_module(f'npcs.{slug}.npc')

    async def generate() -> AsyncGenerator:
        try:
            streaming = await npc_module.main(prompt=query)

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

            done_payload = {'type': 'done', 'text': final_text}
            if streaming.result.pydantic is not None:
                done_payload['mood'] = streaming.result.pydantic.model_dump().get('mood')
            yield _sse(done_payload)
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
