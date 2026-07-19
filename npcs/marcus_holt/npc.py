import asyncio
from pathlib import Path
from crewai.project import load_crew
from crewai import Memory

memory = Memory(
    llm="gpt-5.4-mini",  # Or your hyper-fast local hosting setup
    storage="lancedb",

    # --- Long-Term Priority Tuning ---
    recency_weight=0.1,  # Dampen the effect of time passing
    semantic_weight=0.5,  # Keep semantic similarity as the primary anchor
    importance_weight=0.4,  # Highly important events remain highly relevant
    recency_half_life_days=90,  # A memory takes 3 months to drop half its recency value

    # --- Aggressive Compaction & De-duplication ---
    consolidation_threshold=0.80,  # Merge overlapping context aggressively
    consolidation_limit=8,  # Compare against more history to update state cleanly
    default_importance=0.4,  # Casual chatter defaults lower; standout events pop out

    # --- Latency & Performance Safeties ---
    exploration_budget=0,  # Do NOT run deep multi-turn searches on the live thread
    query_analysis_threshold=250,  # Skip heavy query extraction for standard player prompts

    # --- Multi-Tenant Isolation ---
    root_scope="/games/server_01"  # Isolates memory spaces cleanly per world/server instance
)


async def main(prompt: str) -> dict:
    crew, _ = load_crew(Path(__file__).with_name('crew.jsonc'))
    kickoff = await crew.kickoff_async(inputs={'prompt': prompt})
    response = kickoff.pydantic.model_dump()
    memory.remember(response['response'])
    return response


if __name__ == '__main__':
    print(asyncio.run(main('did i call u a bad word? and what is my name?')))
