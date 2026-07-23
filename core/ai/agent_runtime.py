"""
Streaming kickoff for a standalone crewAI Agent - no Crew, no Task, no JSONC crew file.

Building a Crew (even a one-agent one) means parsing crew.jsonc + agents/*.jsonc,
constructing Task objects, and running the crew's task-orchestration loop on every
kickoff - overhead a single NPC reply doesn't need. Agent.kickoff_async() skips all
of that, but by itself it returns the full LiteAgentOutput only after the whole
response is generated, not token-by-token.

kickoff_streaming() restores that token-by-token behavior by reusing the exact
mechanism Crew.kickoff_async(stream=True) uses under the hood: flip the agent's
LLM into streaming mode and drain LLMStreamChunkEvent off the global crewai event
bus while the kickoff runs in the background. It's the same public event type and
the same crewai.utilities.streaming plumbing crewAI itself relies on for
CrewStreamingOutput - just pointed at a bare agent instead of a crew.
"""

from pydantic import BaseModel
from crewai import Agent
from crewai.crews.utils import enable_agent_streaming
from crewai.lite_agent_output import LiteAgentOutput
from crewai.llms.base_llm import BaseLLM
from crewai.types.streaming import StreamingOutputBase
from crewai.utilities.streaming import create_async_chunk_generator, create_streaming_state, register_cleanup, signal_end, signal_error


class AgentStreamingOutput(StreamingOutputBase[LiteAgentOutput]):

    """
    Streaming output for a standalone Agent.kickoff_async() call.

    Same shape as crewAI's CrewStreamingOutput (async-iterate for chunks, then
    read `.result`) so callers written against CrewStreamingOutput need no changes.

    """

    def _set_result(self, result: LiteAgentOutput) -> None:
        self._result = result
        self._completed = True


async def kickoff_streaming(agent: Agent, prompt: str, response_format: type[BaseModel] | None = None,) -> AgentStreamingOutput:
    """Run agent.kickoff_async(prompt), streaming LLM tokens as they arrive."""
    enable_agent_streaming([agent])

    # enable_agent_streaming() only flips .stream on if agent.llm is a BaseLLM
    # instance - on a crewai upgrade that changes what Agent(llm=...) constructs, or
    # what enable_agent_streaming() checks, this would silently fall back to
    # buffered (whole-response-at-once) output instead of raising. crewai is pinned
    # in pyproject.toml for the same reason; fail loudly here rather than let a
    # version bump quietly turn streaming off.
    if not isinstance(agent.llm, BaseLLM) or not agent.llm.stream:
        raise RuntimeError(
            "enable_agent_streaming() did not put this agent's LLM into streaming "
            "mode - crewai's internals this shim depends on may have changed. "
            "Check agent_runtime.py against the installed crewai version before "
            "bumping the pin in pyproject.toml."
        )

    task_info = {
        'index': 0, 'name': 'conversation', 'id': '',
        'agent_role': agent.role, 'agent_id': str(agent.id),
    }
    result_holder: list[LiteAgentOutput] = []
    state = create_streaming_state(task_info, result_holder, use_async=True)

    async def run_agent() -> None:
        try:
            output = await agent.kickoff_async(prompt, response_format=response_format)
            result_holder.append(output)
        except Exception as exc:
            signal_error(state, exc, is_async=True)
        finally:
            signal_end(state, is_async=True)

    output_holder: list[AgentStreamingOutput] = []
    streaming_output = AgentStreamingOutput(
        async_iterator=create_async_chunk_generator(state, run_agent, output_holder),
    )
    register_cleanup(streaming_output, state)
    output_holder.append(streaming_output)
    return streaming_output
