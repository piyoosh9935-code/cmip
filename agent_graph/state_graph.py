from langgraph.graph import END, StateGraph

from .corrective_rag import make_prepare_retry_node, route_after_verification
from .nodes.generation import make_generation_node
from .nodes.grading import make_grading_node
from .nodes.query_analysis import query_analysis
from .nodes.retrieval import retrieval
from .nodes.verification import make_verification_node
from .state import PipelineState


def _mark_low_confidence(state: dict) -> dict:
    return {
        "low_confidence": True,
        "trace": state.get("trace", []) + [
            {"node": "mark_low_confidence", "detail": "exhausted retries, returning best-effort answer"}
        ],
    }


def build_graph(llm_factory):
    """llm_factory: callable(model_name: str) -> a chat model with .invoke and
    .with_structured_output - either model_routing.ollama_client.get_chat_model for
    real runs, or agent_graph.stub_llm.stub_llm_factory() for fast deterministic tests
    of the graph's wiring."""
    graph = StateGraph(PipelineState)

    graph.add_node("query_analysis", query_analysis)
    graph.add_node("retrieval", retrieval)
    graph.add_node("grading", make_grading_node(llm_factory))
    graph.add_node("generation", make_generation_node(llm_factory))
    graph.add_node("verification", make_verification_node(llm_factory))
    graph.add_node("prepare_retry", make_prepare_retry_node(llm_factory))
    graph.add_node("mark_low_confidence", _mark_low_confidence)

    graph.set_entry_point("query_analysis")
    graph.add_edge("query_analysis", "retrieval")
    graph.add_edge("retrieval", "grading")
    graph.add_edge("grading", "generation")
    graph.add_edge("generation", "verification")
    graph.add_conditional_edges(
        "verification",
        route_after_verification,
        {"end": END, "end_low_confidence": "mark_low_confidence", "retry": "prepare_retry"},
    )
    graph.add_edge("mark_low_confidence", END)
    graph.add_edge("prepare_retry", "retrieval")

    return graph.compile()


def run_query(question: str, member_id: str, llm_factory, max_retries: int = 3) -> dict:
    app = build_graph(llm_factory)
    return app.invoke(
        {
            "question": question,
            "member_id": member_id,
            "retry_count": 0,
            "max_retries": max_retries,
            "trace": [],
        }
    )
