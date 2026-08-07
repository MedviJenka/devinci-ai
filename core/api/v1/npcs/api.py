import asyncio
from collections import defaultdict
from pathlib import Path
from crewai import Agent
from pydantic import BaseModel
from core.ai.agent_runtime import kickoff_streaming
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
    NpcCreateRequest,
    NpcDetail,
    NpcNotFoundError,
    NpcSummary,
    NpcUpdateRequest,
    append_turn,
    build_agent,
    build_response_schema,
    create_npc,
    delete_npc,
    ensure_cached,
    get_npc,
    list_npcs,
    reset_npc_memory,
    sync_memory,
    update_npc,
)

log = Logger(name="npc-service")

# Constructing the Agent rebuilds it from scratch - LLM client init and opening the
# LanceDB memory table - which is expensive enough to dominate response latency if
# repeated on every message. Cached per (user_id, slug) so a given NPC's agent is
# built once per process.
_npc_agents: dict[tuple[str, str], tuple[Agent, type[BaseModel] | None]] = {}
# Serializes calls to a given NPC so two concurrent /talk requests never kick off
# the same cached agent instance at once.
_npc_locks: dict[tuple[str, str], asyncio.Lock] = defaultdict(asyncio.Lock)


def _load_npc_agent(user_id: str, slug: str, cache_dir: Path, npc: NpcDetail) -> tuple[Agent, type[BaseModel] | None]:
    key = (user_id, slug)
    cached = _npc_agents.get(key)
    if cached is not None:
        return cached

    agent = build_agent(cache_dir, npc)
    response_format = build_response_schema(npc.pydantic_fields) if npc.pydantic_enabled else None
    _npc_agents[key] = (agent, response_format)
    return _npc_agents[key]


def _invalidate_npc_cache(user_id: str, slug: str) -> None:
    _npc_agents.pop((user_id, slug), None)
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
        # The cached Agent holds a live handle to the LanceDB memory table that was
        # just deleted out from under it - evict it so the next /talk rebuilds the
        # agent against a fresh (empty) memory store instead of a stale handle.
        _invalidate_npc_cache(user_id, slug)
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc


@router.get('/{slug}/talk')
async def talk_stream(
    slug: str,
    query: str = Query(default=..., description='player query'),
    user_id: str = Depends(get_current_user_id),
) -> StreamingResponse:
    try:
        npc = get_npc(user_id, slug)
        cache_dir = ensure_cached(user_id, slug)
    except NpcNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f'npc "{exc}" not found') from exc

    agent, response_format = _load_npc_agent(user_id, slug, cache_dir, npc)
    lock = _npc_locks[(user_id, slug)]

    async def generate() -> AsyncGenerator:
        try:
            async with lock:
                streaming = await kickoff_streaming(agent, query, response_format)

                # crewAI streams the raw LLM output token-by-token - for structured
                # (output_pydantic) tasks that's fragments of a JSON object like
                # `{"mood": "Happy", "response": "..."}`. Extract the "response"
                # value's text as it arrives instead of waiting for the whole
                # object, so the client sees dialogue appear as it's generated
                # rather than all at once after the full response is done.
                response_streamer = ResponseFieldStreamer()

                async for chunk in streaming:
                    delta = response_streamer.feed(chunk.content)
                    if delta:
                        yield _sse({'type': 'chunk', 'text': delta})

                final_text = streaming.result.raw
                if streaming.result.pydantic is not None:
                    response_text = getattr(streaming.result.pydantic, 'response', None) or final_text
                else:
                    response_text = final_text

                # Catches anything the incremental extraction above didn't emit -
                # e.g. output_pydantic disabled (plain-text task output, no
                # "response" key to find), or a trailing fragment that landed
                # mid-escape-sequence.
                trailing = response_streamer.remainder(response_text)
                if trailing:
                    yield _sse({'type': 'chunk', 'text': trailing})

                # crewAI's TaskOutput.raw isn't guaranteed to be the structured JSON -
                # when the pydantic fields are derived from a plain-text completion via
                # crewAI's converter pass, .raw stays plain narrative text. Send the
                # actual model dump as "text" so structured-output NPCs give clients
                # real JSON to parse/display, not prose that happens to look like it.
                done_text = streaming.result.pydantic.model_dump_json() if streaming.result.pydantic is not None else final_text
                done_payload = {'type': 'done', 'text': done_text}
                if streaming.result.pydantic is not None:
                    # Surfaces every structured field the NPC produced (mood, attitude,
                    # tone, or any custom field added in PersonaEditor) - not just mood -
                    # so the client can react to whatever the NPC's schema defines.
                    done_payload.update(streaming.result.pydantic.model_dump(exclude={'response'}))
                yield _sse(done_payload)
        except Exception as exc:
            log.fire.error(f'stream failed: {exc}')
            yield _sse({'type': 'error', 'message': 'Failed to generate response.'})
            return

        # Outside the lock: it only needs to protect the shared cached crew instance
        # during kickoff. Memory sync can be slow (grows with conversation length,
        # see sync_memory) and has no business blocking the next /talk call for this
        # NPC from starting its own kickoff while it finishes uploading.
        try:
            sync_memory(user_id, slug)
        except Exception as exc:
            log.fire.error(f'memory sync failed: {exc}')

        # A separate, best-effort record from memory sync above: memory is crewAI's
        # heuristic recall of the player, this is the raw transcript of what was
        # actually said this turn (see append_turn). One failing independently of
        # the other shouldn't take down either.
        try:
            turn_fields = {'query': query, 'response': response_text}
            if streaming.result.pydantic is not None:
                turn_fields.update(streaming.result.pydantic.model_dump(exclude={'response'}))
            append_turn(user_id, slug, turn_fields)
        except Exception as exc:
            log.fire.error(f'transcript append failed: {exc}')

    return StreamingResponse(
        generate(),
        media_type='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no',
        },
    )
