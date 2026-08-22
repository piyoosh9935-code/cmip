from llmops.mlflow.metrics import precision_at_k, recall_at_k


def test_precision_at_k_all_relevant():
    assert precision_at_k(["a", "b", "c"], {"a", "b", "c"}, k=3) == 1.0


def test_precision_at_k_partial():
    assert precision_at_k(["a", "x", "b"], {"a", "b"}, k=3) == 2 / 3


def test_precision_at_k_empty_retrieved():
    assert precision_at_k([], {"a"}, k=5) == 0.0


def test_recall_at_k_all_found():
    assert recall_at_k(["a", "b", "c"], {"a", "b"}, k=3) == 1.0


def test_recall_at_k_partial():
    assert recall_at_k(["a"], {"a", "b"}, k=5) == 0.5


def test_recall_at_k_no_relevant_docs_is_zero_not_divide_by_zero():
    assert recall_at_k(["a", "b"], set(), k=5) == 0.0


def test_recall_at_k_respects_k_cutoff():
    # relevant doc "c" is outside the top-2 window
    assert recall_at_k(["a", "b", "c"], {"c"}, k=2) == 0.0
