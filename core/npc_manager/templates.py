DEFAULT_LLM = 'openai/gpt-5.5'

# Filenames written by code paths that no longer exist: 'schema.py' predates
# 'schemas.py'; 'voice.json' was per-NPC TTS settings for a feature not present on
# this branch; 'agent.jsonc'/'output_schema.jsonc'/'schemas.py'/'README.md' predate
# the switch to a self-contained npc.py, which in turn was replaced by npc.json (see
# _render_npc_config) once nothing needed the config as importable code anymore -
# build_agent/build_response_schema construct the Agent and structured-output schema
# directly from the parsed config instead. Nothing reads these; update_npc prunes them
# from storage/cache on touch.
LEGACY_FILES = (
    'npc.py', 'schema.py', 'voice.json', 'agent.jsonc', 'output_schema.jsonc', 'schemas.py', 'README.md',
)

DEFAULT_PERSONA_NOTES = '''# {display_name}

**Age:**
**Occupation:**

## Backstory

{backstory}

## Personality

## Known Facts

## Quest

**important:** if users asks question regarding the quest, do not ignore it
---

'''

STRICT_RULES = '''
**STRICT RULES**
- no sexual content
- if the user annoys you, respond with: "I don't want to talk to you anymore... come back later when I calm down"'''

SKILL_MD = '''
---
name: {slug}
description: {description}
---

''' + STRICT_RULES + '''

{persona_notes}
'''
