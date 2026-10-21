"""Structured proposals and stage results. IDs refer to Markdown table entries."""

OPERATIONS = ["ADD", "UPDATE", "DELETE", "MERGE", "NO_CHANGE", "NEEDS_REVIEW"]


def obj(properties: dict) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def array(items: dict) -> dict:
    return {"type": "array", "items": items}


TEXT = {"type": "string"}
NULLABLE_TEXT = {"type": ["string", "null"]}
EVIDENCE = obj({
    "kind": {"enum": ["source", "diff", "conversation", "memory"]},
    "path": NULLABLE_TEXT, "line": {"type": ["integer", "null"], "minimum": 1},
    "session": NULLABLE_TEXT, "message": NULLABLE_TEXT, "quote": TEXT,
})
COVERAGE = obj({"files_read": array(TEXT), "sessions_read": array(TEXT), "notes": TEXT})
RECORD = obj({
    "target": TEXT, "fact_id": NULLABLE_TEXT, "merge_ids": array(TEXT),
    "op": {"enum": OPERATIONS}, "text": TEXT, "scope": TEXT,
    "evidence": array(EVIDENCE), "reason": TEXT,
})
FINDING = obj({"summary": TEXT, "suggested_home": TEXT, "evidence": array(EVIDENCE)})
HANDOFF = obj({"to": TEXT, "note": TEXT, "evidence": array(EVIDENCE)})
SWEEPER_OUTPUT = obj({
    "findings": array(FINDING), "handoffs": array(HANDOFF),
    "contradictions": array(TEXT), "unresolved": array(TEXT), "coverage": COVERAGE,
})
WORKER_OUTPUT = obj({
    "records": array(RECORD), "handoffs": array(HANDOFF),
    "unowned": array(FINDING), "coverage": COVERAGE,
})
WORKER_OUTPUT["properties"]["records"]["minItems"] = 1
CARTOGRAPHER_OUTPUT = obj({"proposals": array(obj({
    "kind": {"enum": ["core-file", "product-folder"]}, "path": TEXT,
    "rationale": TEXT, "seed_entries": array(TEXT), "definition_draft": TEXT,
    "index_line": TEXT, "finding_refs": array(TEXT),
}))})
WRITER_OUTPUT = obj({
    "applied": array(obj({"record_id": TEXT})),
    "skipped": array(obj({"record_id": TEXT, "reason": TEXT})),
})
