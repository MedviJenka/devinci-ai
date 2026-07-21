"""
Workaround for crewAIInc/crewAI#6585.

Relative "skills" paths in JSON/JSONC agent configs are resolved against the
process's current working directory instead of the project root, unlike
every other path field (tools, output_pydantic, input_files). That makes the
same crew definition succeed or fail depending on where the process happens
to be launched from (e.g. a server started outside the crew's own
directory), which is exactly what breaks story/npc crews when run through
the API instead of as a standalone script.

Patches crewai.project.json_loader so relative "skills" entries are resolved
against project_root at agent-load time, matching tools/output_pydantic.
Remove once upstream ships a fix (linked PRs: #6587, #6596).
"""

from pathlib import Path
from typing import Any
from crewai.project import json_loader as _json_loader


_original_resolve_agent_python_refs = _json_loader._resolve_agent_python_refs


def _resolve_skill_entry(entry: Any, root: Path) -> Any:
    if not isinstance(entry, str) or entry.startswith("@") or entry.lstrip().startswith("---"):
        return entry
    path = Path(entry)
    return entry if path.is_absolute() else str((root / path).resolve())


def _patched_resolve_agent_python_refs(kwargs: dict[str, Any], source: Any, project_root: Path | None) -> None:
    _original_resolve_agent_python_refs(kwargs, source, project_root)
    skills = kwargs.get("skills")
    if not isinstance(skills, list):
        return
    root = Path(project_root).resolve() if project_root is not None else Path.cwd()
    kwargs["skills"] = [_resolve_skill_entry(entry, root) for entry in skills]


_json_loader._resolve_agent_python_refs = _patched_resolve_agent_python_refs
