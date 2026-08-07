# Plan: Per-NPC Agent System — As-Built + Next Steps

> Rewritten from a first-principles look at this actual repo. The previous
> version of this document was drafted without reading the codebase: it
> assumed a from-scratch two-NPC game prototype driven entirely by an
> `omp --mode rpc` subprocess harness. Neither premise holds here — see
> §7 for why Oh My Pi was evaluated and dropped, backed by measurements,
> not vibes.

## 0. What this project actually is

A multi-tenant NPC-creation SaaS, not a fixed two-NPC demo:

- **Frontend** (`frontend/`): React/TS app — NPC library, persona editor,
  dashboard, chat UI.
- **Backend** (`core/`): FastAPI, versioned under `/api/v1/...`
  (`core/api/v1/npcs`, `.../voice`, `.../story_creation`, `.../api_keys`).
- **NPCs are per-user data**, not files checked into the repo. Each NPC is a
  small bundle of config + a `SKILL.md` persona pack + a memory store, keyed
  by `(user_id, slug)` and persisted in **Supabase Storage**.
- **The dialogue harness is crewAI's own `Agent`**, used directly — no Crew,
  no Task, no custom RPC layer, no per-NPC subprocess.
- `game/` is a standalone pygame demo client that hits the real `/talk` SSE
  endpoint over HTTP; it's an example consumer, not part of the runtime.

## 1. Confirmed architecture (as it exists today)

| Concern | Implementation | Where |
|---|---|---|
| Per-NPC identity | `npc.json` (role/goal/backstory/llm/pydantic schema) | `core/npc_manager/service.py` |
| Knowledge pack | One `SKILL.md` per NPC (frontmatter `name`/`description` + STRICT_RULES + persona notes) | `core/npc_manager/templates.py`, `service.py::_write_skill_md` |
| Persistence | Supabase Storage, bucket `Config.NPC_STORAGE_BUCKET`, key prefix `{user_id}/{slug}/` | `core/npc_manager/paths.py`, `core/storage/client.py` |
| Execution harness | **crewAI `Agent`** built with `skills=[cache_dir/skills]`, `memory=Memory(storage=cache_dir/memory)` | `core/npc_manager/engine.py::build_agent` |
| Local working copy | Storage synced on demand into `Config.NPC_CACHE_DIR` (`./.npc_cache/{user_id}/{slug}/`); crewAI needs real files on disk for skills + LanceDB | `core/npc_manager/storage_io.py::ensure_cached` |
| Agent reuse | One crewAI `Agent` object cached in-process per `(user_id, slug)`, an `asyncio.Lock` per NPC serializes concurrent `/talk` calls against it | `core/api/v1/npcs/api.py` |
| Dialogue turn | `GET /api/v1/npcs/{slug}/talk?query=...`, SSE stream of token chunks via `kickoff_streaming` | `core/api/v1/npcs/api.py`, `core/ai/agent_runtime.py` |
| Structured output | Runtime-built Pydantic schema (`mood`, `attitude`, `tone`, `response`, + custom fields) | `core/npc_manager/schemas.py`, `engine.py::build_response_schema` |
| Memory | crewAI's LanceDB-backed `Memory`, written locally then pushed to Supabase Storage after each turn (`sync_memory`); pulled back down by `ensure_cached` | `core/npc_manager/storage_io.py` |
| Voice | OpenAI `gpt-4o-mini-tts`, streamed as mp3 chunks, tone-aware instructions | `core/voice/engine.py`, `core/api/v1/voice/api.py` |

```mermaid
graph LR
  U[Player / user] -->|GET /talk?query=| API[FastAPI npc_router]
  API --> Cache{cached Agent for<br/>(user_id, slug)?}
  Cache -->|miss| Sync[ensure_cached:<br/>Supabase Storage → local .npc_cache]
  Sync --> Build[build_agent:<br/>crewAI Agent + skills + Memory]
  Build --> Cache
  Cache -->|hit| Kickoff[kickoff_streaming<br/>Agent.kickoff_async, token stream]
  Kickoff -->|SSE chunks| U
  Kickoff --> SyncMem[sync_memory:<br/>local LanceDB → Supabase Storage]
  API --> Voice[POST /voice/speak → OpenAI TTS<br/>streamed mp3]
```

## 2. Storage layout (Supabase Storage, bucket = `NPC_STORAGE_BUCKET`)

```text
{user_id}/
  {slug}/
    npc.json                     # role, goal, backstory, llm, pydantic schema
    skills/
      {slug}/
        SKILL.md                 # frontmatter (name, description) + STRICT_RULES + persona notes
    memory/                      # LanceDB files (append-only, synced incrementally)
```

Local execution cache mirrors this 1:1 under `NPC_CACHE_DIR` (default
`./.npc_cache/{user_id}/{slug}/`). The cache is **disposable** — it's rebuilt
from Storage by `ensure_cached` on first use per process, which is what lets
the backend run as multiple stateless replicas and survive restarts without
losing anything: Storage is the source of truth, the local cache is a working
copy.

## 3. `SKILL.md` schema (as implemented)

```md
---
name: {slug}
description: {goal}
---

**STRICT RULES**
- no sexual content
- if the user annoys you, respond with: "I don't want to talk to you anymore... come back later when I calm down"

{persona_notes}
```

`persona_notes` is free-form markdown (age/occupation/backstory/personality/
known facts — see `_DEFAULT_PERSONA_NOTES` in `templates.py`), authored
through the Persona Editor in the frontend.

**Note on custom metadata (e.g. quest linkage):** the previous plan invented
`impact_on_quest`, `quest_id`, `age` as arbitrary top-level frontmatter keys.
I checked crewAI's actual frontmatter model
(`crewai/skills/models.py::SkillFrontmatter`) — it only recognizes `name`,
`description`, `license`, `compatibility`, `allowed-tools`, and one general
escape hatch: `metadata: dict[str, str]`. If this product ever wants
NPC-level structured tags like that, they'd need to go under a `metadata:`
map with string values, e.g.:

```yaml
metadata:
  quest_id: "drowned_chapel"
  impact_on_quest: "true"
```

not as bare top-level keys — those would be silently ignored. This isn't
built currently and there's no "quest" concept anywhere in this codebase
today (the original plan's Eldrin/Emberkey/ravine lore was entirely invented
for a generic demo and has nothing to do with this product) — flagged here
only so it's not silently unsupported if it comes up later.

## 4. Full-body injection — already guaranteed, no boot-injection hack needed

The original plan spent a whole section (old §6) on a workaround for omp
only exposing name+description by default and needing a "reply with only
the word: ready" boot prompt to force the full pack into context, because
full-body auto-injection was "build-dependent... must be verified, not
assumed."

That problem doesn't exist here. Read `crewai/skills/loader.py`:
`Agent(skills=[path])` calls `load_skill(path)` →
`discover_skills` + `activate_skill` for *every* skill found, and
`activate_skill` unconditionally promotes it to `INSTRUCTIONS` level (full
`SKILL.md` body loaded) at Agent-construction time — not on first use, not
gated on a description match. Since `_npc_agents` caches the built `Agent`
per `(user_id, slug)` for the life of the process, that full body is resident
for every subsequent `/talk` call against it. No verification step needed;
it's unconditional in the library source.

## 5. Memory — already persistent, heuristic by design

`Agent(memory=Memory(storage=cache_dir/memory))` gives each NPC its own
LanceDB memory table. It:

- writes locally during a conversation (crewAI requires real files on disk),
- gets pushed to Supabase Storage after each turn by `sync_memory` (only
  files not already known-synced, since LanceDB is append-only and a full
  re-upload every turn would make each message slower than the last),
- gets pulled back down by `ensure_cached` the next time this `(user_id,
  slug)` is loaded into a fresh process.

This already satisfies the original plan's "NPC remembers the player across
encounters" requirement — no omp `local`/`mnemopi` backend needed. It's
already heuristic/semantic-summary memory, not a literal transcript — which
is the one real gap, addressed next.

## 6. Real gap: no per-conversation transcript ("diff file")

Nothing today writes a raw, append-only, turn-by-turn conversation log. If
that's wanted (debugging, analytics, moderation review, "what exactly did
Eldrin say last Tuesday"), it doesn't need omp — the existing `sync_memory`
pattern already shows the cheap way to do it in this architecture:

1. In `talk_stream`'s `generate()`, after `final_text`/`response_text` are
   known, append one JSON line to a local file: `sessions/{slug}/{session
   or date}.jsonl` — `{ts, query, response, mood/attitude/tone if present}`.
2. Sync that file to Supabase Storage the same way `sync_memory` already
   syncs `memory/` (append-only, only-upload-new-bytes).
3. `ensure_cached` already pulls arbitrary files under the NPC's prefix down
   into the cache dir, so no change needed there.

This is a small, additive change to `storage_io.py` + `api.py`, not a new
subsystem.

## 7. Why Oh My Pi (`omp`) is not the harness — measured, not assumed

Both stated motivations were tested directly against this repo's real
alternative rather than argued about in the abstract.

### 7.1 Dialogue harness (execution model mismatch)

`omp --mode rpc` is a long-lived **subprocess per session**. This backend's
whole design — stateless request handlers, Supabase Storage as source of
truth, a disposable local cache — is what lets it run as multiple replicas
and survive restarts for free. A subprocess pool keyed by `(user_id, slug)`
isn't visible across replicas and would require re-inventing the
warm-instance/eviction bookkeeping `_npc_agents`/`_npc_locks` already does,
just heavier (an OS process instead of a Python object). And §4 shows the
one problem omp's RPC path was solving (uncertain full-skill injection)
is already solved unconditionally by crewAI here.

### 7.2 Voice (measured latency, not projected)

Ran `omp say` locally against this machine, twice (first run downloads the
ONNX/Kokoro model; second run is the steady state):

```
$ time omp say "Greetings, traveler. What brings you to my humble stall..." --out test.wav
saved test.wav (af_heart, kokoro, 6.1s audio, 291644 bytes)
real  0m10.141s   # includes model fetch

$ time omp say "My name is Allbert, welcome to my stall." --out test.wav
saved test.wav (af_heart, kokoro, 3.8s audio, 180044 bytes)
real  0m7.432s    # warm, no download
```

`omp say` is a one-shot CLI invocation — Node process start + ONNX model
init on every call, not a warm daemon — and it writes a complete WAV file
before returning (no progressive/streaming output). **7–10 seconds
wall-clock for one short line**, versus the current `core/voice/engine.py`
path (OpenAI `gpt-4o-mini-tts`, `stream_bytes`, sub-second time-to-first-byte
today) which is already what's live in `POST /api/v1/voice/speak`. Swapping
to `omp say` would make voice responses roughly an order of magnitude
slower, not faster — the opposite of the stated goal.

If local/offline TTS becomes worth revisiting later (e.g. for cost, not
speed), the right shape would be a **long-lived warm process** hosting the
Kokoro/ONNX model directly (or via omp's `acp`/RPC server mode, if it
exposes `say` as an in-session tool rather than a fresh CLI call — not yet
confirmed) rather than spawning `omp say` per request. Not pursued now: no
evidence it's needed, and it would add a local ML-inference dependency to
the deploy (`Dockerfile`/`compose.yaml`) for a capability the OpenAI path
already covers at better latency.

## 8. Open extension points (not required for v1, unchanged in spirit from before)

- Per-conversation transcript log (§6) — cheapest, most concrete win.
- `core/npc_manager/dynamics.py` (`DynamicMoodSchema`, `trust_level`) exists
  as a stub, not wired into `engine.py`/`api.py` — a real "quest impact"/
  relationship-state feature could build on it plus the `metadata:`
  frontmatter convention in §3, if this product ever wants that.
- Router agent that picks which NPC a message is addressed to (not needed
  today — one NPC per `/talk` call, selected by `slug` in the URL).
- Revisit local/offline TTS as a warm daemon (§7.2) if cost, not speed,
  becomes the driver.
