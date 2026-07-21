import importlib.util
from core.useful.log import Logger
from core.useful.stream import _sse
from core.settings import Config
from typing import AsyncGenerator
from core.useful.auth import get_current_user_id
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, HTTPException, Query, FastAPI
from core.useful.npc_manager import (
    NpcAlreadyExistsError,
    NpcCreateRequest,
    NpcDetail,
    NpcNotFoundError,
    NpcSummary,
    NpcUpdateRequest,
    create_npc,
    delete_npc,
    ensure_cached,
    get_npc,
    list_npcs,
    update_npc,
)

log = Logger(name="npc-service")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator:
    log.fire.info(f'{log.name} started successfully')
    yield
    log.fire.info(f'{log.name} stopped successfully')


router = APIRouter(prefix=f'/api/{Config.API_VERSION}/npcs', lifespan=lifespan)



@router.get('/')
async def list_npcs_route(user_id: str = Depends(get_current_user_id)) -> list[NpcSummary]:
    return list_npcs(user_id)


@router.post('/', status_code=201)
async def create_npc_route(req: NpcCreateRequest, user_id: str = Depends(get_current_user_id)) -> NpcDetail:
    try:
        return create_npc(user_id, req)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NpcAlreadyExistsError as exc:
        raise HTTPException(status_code=409, detail=f'npc "{exc}" already exists') from exc


@router.get('/{slug}')
async def get_npc_route(slug: str, user_id: str = Depends(get_current_user_id)) -> NpcDetail:
    try:
        return get_npc(user_id, slug)
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc


@router.put('/{slug}')
async def update_npc_route(
    slug: str, req: NpcUpdateRequest, user_id: str = Depends(get_current_user_id),
) -> NpcDetail:
    try:
        return update_npc(user_id, slug, req)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc


@router.delete('/{slug}', status_code=204)
async def delete_npc_route(slug: str, user_id: str = Depends(get_current_user_id)) -> None:
    try:
        delete_npc(user_id, slug)
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc


@router.get('/{slug}/talk')
async def talk_stream(
    slug: str,
    query: str = Query(default=..., description='player query'),
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    try:
        get_npc(user_id, slug)
        cache_dir = ensure_cached(user_id, slug)
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc

    module_name = f'_npc_{user_id}_{slug}'.replace('-', '_')
    spec = importlib.util.spec_from_file_location(module_name, cache_dir / 'npc.py')
    npc_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(npc_module)

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
