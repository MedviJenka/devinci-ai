import asyncio
from collections import defaultdict
from core.ai.npc_llm import stream_reply
from core.useful.log import Logger
from core.useful.stream import _sse
from core.useful.json_stream import ResponseFieldStreamer
from core.settings import Config
from typing import AsyncGenerator
from core.useful.auth import get_current_user_id
from fastapi.responses import StreamingResponse
from contextlib import asynccontextmanager
from fastapi import APIRouter, Depends, HTTPException, Query, FastAPI
from core.npc_manager import (
    NpcAlreadyExistsError,
    NpcContext,
    NpcCreateRequest,
    NpcDetail,
    NpcNotFoundError,
    NpcSummary,
    NpcUpdateRequest,
    append_turn,
    build_npc_context,
    create_npc,
    delete_npc,
    ensure_cached,
    get_npc,
    list_npcs,
    load_recent_turns,
    reset_npc_memory,
    update_npc,
)

log = Logger(name="npc-service")

# Loading an NPC means several storage round trips (get_npc's config + SKILL.md reads,
# ensure_cached on a cold cache) - enough to noticeably delay the first token if paid
# on every message. Cached per (user_id, slug) so it's paid once per process, and
# evicted by every route that changes what it was built from.
_npc_contexts: dict[tuple[str, str], NpcContext] = {}
# Serializes calls to a given NPC so two concurrent /talk requests never interleave -
# each turn must see the previous one in its history.
_npc_locks: dict[tuple[str, str], asyncio.Lock] = defaultdict(asyncio.Lock)


def _load_npc_context(user_id: str, slug: str) -> NpcContext:
    key = (user_id, slug)
    cached = _npc_contexts.get(key)
    if cached is not None:
        return cached

    npc = get_npc(user_id, slug)
    cache_dir = ensure_cached(user_id, slug)
    _npc_contexts[key] = build_npc_context(cache_dir, npc)
    return _npc_contexts[key]


def _invalidate_npc_cache(user_id: str, slug: str) -> None:
    _npc_contexts.pop((user_id, slug), None)
    _npc_locks.pop((user_id, slug), None)


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
        result = update_npc(user_id, slug, req)
        _invalidate_npc_cache(user_id, slug)
        return result
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc


@router.delete('/{slug}', status_code=204)
async def delete_npc_route(slug: str, user_id: str = Depends(get_current_user_id)) -> None:
    try:
        delete_npc(user_id, slug)
        _invalidate_npc_cache(user_id, slug)
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc


@router.delete('/{slug}/memory', status_code=204)
async def reset_npc_memory_route(slug: str, user_id: str = Depends(get_current_user_id)) -> None:
    try:
        reset_npc_memory(user_id, slug)
        # reset_npc_memory wipes the local cache's memory/ dir along with storage's -
        # evict the cached context too so nothing about the old conversation lingers.
        _invalidate_npc_cache(user_id, slug)
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc


@router.get('/{slug}/history')
async def history_route(slug: str, user_id: str = Depends(get_current_user_id)) -> list[dict]:
    """The recent turns the NPC currently remembers - exactly the window /talk replays
    to the model - so clients can show the conversation the NPC will continue from."""
    try:
        ensure_cached(user_id, slug)
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc
    return load_recent_turns(user_id, slug, Config.NPC_HISTORY_TURNS)


@router.get('/{slug}/talk')
async def talk_stream(
    slug: str,
    query: str = Query(default=..., description='player query'),
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    try:
        ctx = _load_npc_context(user_id, slug)
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    lock = _npc_locks[(user_id, slug)]

    async def generate() -> AsyncGenerator:
        async with lock:
            try:
                history = load_recent_turns(user_id, slug, Config.NPC_HISTORY_TURNS)
                # Structured NPCs stream a JSON object like `{"mood": "Happy", "response": "..."}`
                # one fragment at a time - extract the "response" value's text as it arrives
                # instead of waiting for the whole object, so dialogue appears as it's generated.
                response_streamer = ResponseFieldStreamer() if ctx.response_format is not None else None

                async with stream_reply(ctx, history, query) as stream:
                    async for event in stream:
                        if event.type != 'response.output_text.delta':
                            continue
                        delta = response_streamer.feed(event.delta) if response_streamer else event.delta
                        if delta:
                            yield _sse({'type': 'chunk', 'text': delta})
                    final = await stream.get_final_response()

                parsed = final.output_parsed if ctx.response_format is not None else None
                if ctx.response_format is not None and parsed is None:
                    # Strict schema mode only skips the schema on a refusal or a cut-off reply.
                    raise RuntimeError(f'no structured output (status={final.status})')

                if parsed is not None:
                    response_text = getattr(parsed, 'response', None) or final.output_text
                    # Catches a trailing fragment the incremental extraction above held back
                    # mid-escape-sequence, or a schema with no "response" field at all.
                    trailing = response_streamer.remainder(response_text)
                    if trailing:
                        yield _sse({'type': 'chunk', 'text': trailing})
                    # Surfaces every structured field the NPC produced (mood, attitude, tone,
                    # or any custom field added in PersonaEditor) so the client can react to
                    # whatever the NPC's schema defines, with the full JSON as "text".
                    extra_fields = parsed.model_dump(exclude={'response'})
                    yield _sse({'type': 'done', 'text': parsed.model_dump_json(), **extra_fields})
                else:
                    response_text = final.output_text
                    extra_fields = {}
                    yield _sse({'type': 'done', 'text': response_text})
            except Exception as exc:
                log.fire.error(f'stream failed: {exc}')
                yield _sse({'type': 'error', 'message': 'Failed to generate response.'})
                return

            # After `done` has gone out, so the player never waits on it - but still under
            # the lock, so the next message to this NPC sees this turn in its history.
            try:
                append_turn(user_id, slug, {'query': query, 'response': response_text, **extra_fields})
            except Exception as exc:
                log.fire.error(f'turn append failed: {exc}')

    return StreamingResponse(
        generate(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )
