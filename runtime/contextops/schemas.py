"""JSON schemas the Agent SDK enforces on each agent's final answer.

The change record mirrors maintenance/core.md#change-record. Keep the two in sync.
"""

OPERATIONS = ["ADD", "UPDATE", "DELETE", "MERGE", "NO_CHANGE", "NEEDS_REVIEW"]

EVIDENCE = {
    "type": "object",
    "properties": {
        "kind": {"enum": ["conversation", "diff", "source", "memory"]},
        "session": {"type": "string"},
        "message": {"type": "string"},
        "path": {"type": "string"},
        "line": {"type": "integer"},
        "quote": {"type": "string", "description": "Short verbatim excerpt supporting the claim"},
    },
    "required": ["kind"],
}

CHANGE_RECORD = {
    "type": "object",
    "properties": {
        "target": {"type": "string", "description": "Knowledge document path, relative to the bundle"},
        "fact_id": {"type": ["string", "null"]},
        "op": {"enum": OPERATIONS},
        "text": {"type": "string", "description": "Final wording as it should appear in the document"},
        "scope": {"type": "string", "description": "company, app:<name>, or tool:<name>"},
        "evidence": {"type": "array", "items": EVIDENCE},
        "reason": {"type": "string"},
    },
    "required": ["target", "fact_id", "op", "text", "scope", "evidence", "reason"],
}

HANDOFF = {
    "type": "object",
    "properties": {
        "to": {"type": "string", "description": "Path of the document that owns this finding"},
        "note": {"type": "string"},
        "evidence": {"type": "array", "items": EVIDENCE},
    },
    "required": ["to", "note", "evidence"],
}

UNOWNED = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "suggested_home": {"type": "string"},
        "evidence": {"type": "array", "items": EVIDENCE},
    },
    "required": ["summary", "suggested_home", "evidence"],
}

# One schema for the sweeper and every specialist. The SDK sends the schema as a tool
# definition, which sits at the front of the prompt cache prefix; a fork whose schema
# differed from its sweeper's would re-write the whole inherited history to the cache.
AGENT_OUTPUT = {
    "type": "object",
    "properties": {
        "records": {"type": "array", "items": CHANGE_RECORD,
                    "description": "Change records. Specialists only; the sweeper returns an empty list"},
        "findings": {"type": "array", "items": UNOWNED,
                     "description": "Sweeper candidates for the specialists; specialists return an empty list"},
        "handoffs": {"type": "array", "items": HANDOFF},
        "unowned": {"type": "array", "items": UNOWNED,
                    "description": "Supported findings no specialist document can hold; the sweeper returns an empty list"},
        "contradictions": {"type": "array", "items": {"type": "string"}},
        "unresolved": {"type": "array", "items": {"type": "string"}},
        "coverage": {
            "type": "object",
            "properties": {
                "sessions_read": {"type": "array", "items": {"type": "string"}},
                "files_read": {"type": "array", "items": {"type": "string"}},
                "notes": {"type": "string"},
            },
            "required": ["sessions_read", "files_read", "notes"],
        },
    },
    "required": ["records", "findings", "handoffs", "unowned", "contradictions", "unresolved", "coverage"],
}

WORKER_OUTPUT = AGENT_OUTPUT

CARTOGRAPHER_OUTPUT = {
    "type": "object",
    "properties": {
        "proposals": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "kind": {"enum": ["core-file", "tool-folder"]},
                    "path": {"type": "string"},
                    "type": {"type": "string"},
                    "scope": {"type": "string"},
                    "rationale": {"type": "string"},
                    "seed_entries": {"type": "array", "items": {"type": "string"}},
                    "agent_draft": {"type": "string"},
                    "index_line": {"type": "string"},
                    "finding_refs": {"type": "array", "items": {"type": "string"}},
                },
                "required": [
                    "kind", "path", "type", "scope", "rationale",
                    "seed_entries", "agent_draft", "index_line", "finding_refs",
                ],
            },
        },
    },
    "required": ["proposals"],
}

_APPLIED = {
    "type": "object",
    "properties": {
        "target": {"type": "string"},
        "fact_id": {"type": ["string", "null"]},
        "op": {"enum": OPERATIONS},
    },
    "required": ["target", "fact_id", "op"],
}

WRITER_OUTPUT = {
    "type": "object",
    "properties": {
        "applied": {"type": "array", "items": _APPLIED},
        "skipped": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "target": {"type": "string"},
                    "fact_id": {"type": ["string", "null"]},
                    "reason": {"type": "string"},
                },
                "required": ["target", "fact_id", "reason"],
            },
        },
        "log_entry": {"type": "string"},
    },
    "required": ["applied", "skipped", "log_entry"],
}
