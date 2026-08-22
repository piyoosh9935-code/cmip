"""Every retrieved Document needs a stable, unique citation id regardless of which
retriever produced it - this is what the LangGraph verification node checks cited ids
against (see langgraph/nodes/verification.py)."""

import hashlib

from langchain_core.documents import Document


def get_doc_id(doc: Document) -> str:
    md = doc.metadata
    source = md.get("source")
    if source == "qdrant":
        return f"{md['note_id']}:{md.get('chunk_index', 0)}"
    if source == "bm25":
        return md["note_id"]
    if source == "sql":
        intent = md.get("intent")
        if intent == "claims_history":
            return f"claim:{md['claim_id']}"
        if intent == "recent_encounters":
            return f"encounter:{md['encounter_id']}"
        if intent == "medication_list":
            return f"medication:{md.get('medication_id') or md['medication_name']}"
        if intent == "sdoh_profile":
            return f"sdoh:{md['member_id']}"
        if intent == "member_summary":
            return f"summary:{md['member_id']}"
    return hashlib.sha1(doc.page_content.encode()).hexdigest()[:12]
