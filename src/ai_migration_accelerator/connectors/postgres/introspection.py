from __future__ import annotations


def pgvector_capabilities() -> dict[str, object]:
    return {
        "supports_vector": True,
        "recommended_index": "ivfflat",
        "metadata_column": "jsonb",
    }
