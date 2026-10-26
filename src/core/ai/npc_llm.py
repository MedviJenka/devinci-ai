"""
Single-call NPC reply generation straight on the OpenAI Responses API.

Replaces the crewAI Agent on the /talk path. A crewAI kickoff chained several LLM
round trips per player message - "deep" memory recall analysis before the reply,
a ReAct loop with memory tools, and memory extraction + embedding after it - all
before the `done` event could go out. This makes exactly one streaming call, with
structured output enforced by the API's strict JSON-schema mode rather than a
converter pass, so time-to-first-token is just the model's own latency.
"""

import re
from functools import cache
from typing import Any
from openai import AsyncOpenAI, Omit, omit
from openai.lib.streaming.responses import AsyncResponseStreamManager
from core.npc_manager import NpcContext
from core.settings import Config


@cache
def _client() -> AsyncOpenAI:
    # Created lazily so importing the API module doesn't require OPENAI_API_KEY
    # to be set (e.g. for the e2e suite, which mocks /talk entirely).
    return AsyncOpenAI(api_key=Config.OPENAI_API_KEY or None)


def _build_input(ctx: NpcContext, history: list[dict], query: str) -> list[dict[str, Any]]:
    messages: list[dict[str, Any]] = [{'role': 'system', 'content': ctx.system_prompt}]
    for turn in history:
        messages.append({'role': 'user', 'content': turn['query']})
        messages.append({'role': 'assistant', 'content': turn['response']})
    messages.append({'role': 'user', 'content': query})
    return messages


def _reasoning(model: str) -> dict[str, str] | Omit:
    effort = Config.NPC_REASONING_EFFORT
    if not effort or not model.startswith(('gpt-5', 'o1', 'o3', 'o4')):
        return omit
    # 'none' only exists from gpt-5.1 on - the original gpt-5 family's floor is 'minimal'.
    if effort == 'none' and re.match(r'gpt-5(-|$)', model):
        effort = 'minimal'
    # ...and the o-series' floor is 'low'.
    elif effort in ('none', 'minimal') and model.startswith('o'):
        effort = 'low'
    return {'effort': effort}


def stream_reply(ctx: NpcContext, history: list[dict], query: str) -> AsyncResponseStreamManager:
    """Open a streaming reply. Use as `async with stream_reply(...) as stream:`, iterate
    it for `response.output_text.delta` events, then `await stream.get_final_response()`
    - its `.output_parsed` is the NPC's response_format instance when one is set."""
    return _client().responses.stream(
        model=ctx.model,
        input=_build_input(ctx, history, query),
        text_format=ctx.response_format if ctx.response_format is not None else omit,
        reasoning=_reasoning(ctx.model),
        store=False,
    )
