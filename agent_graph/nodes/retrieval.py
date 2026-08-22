from retrieval.ensemble_retriever import build_ensemble_retriever


def retrieval(state: dict) -> dict:
    query = state.get("rewritten_query") or state["question"]
    retriever = build_ensemble_retriever(
        member_id=state["member_id"], k=5, weights=state.get("retrieval_weights")
    )
    docs = retriever.invoke(query)

    return {
        "retrieved_docs": docs,
        "trace": state.get("trace", []) + [
            {"node": "retrieval", "detail": f"query={query!r} -> {len(docs)} docs, weights={state.get('retrieval_weights')}"}
        ],
    }
