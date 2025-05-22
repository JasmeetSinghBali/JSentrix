# pytest ./tests/test_hybrid_scoring_langchain_retriever.py -s
import pytest
import json
from datetime import datetime, timedelta, timezone

from memory.langchain_retriever import GraphMemoryRetriever

@pytest.fixture
def memory():
    return GraphMemoryRetriever()

@pytest.mark.parametrize("mode", ["hybrid", "decay", "default"])
def test_scoring_modes(memory, mode):
    """
    Tests each scoring mode in isolation to avoid mutation of last_accessed_at.
    - hybrid: similarity × decay (rescore=True)
    - decay: decay only (apply_decay=True, rescore=False)
    - default: vectorstore similarity only (apply_decay=False, rescore=False)
    """
    stale_text = "The transfer limit is $10,000 per month."
    fresh_text = "The transfer limit is $5,000 per week."  # Slightly different

    now = datetime.now(timezone.utc)
    stale_time = (now - timedelta(days=30)).isoformat()
    fresh_time = now.isoformat()

    # Stale doc: high similarity, but old last_accessed_at
    stale_meta = {
        "clause_id": "C_STALE",
        "clause_type": "Limit",
        "score": 0.95,
        "last_accessed_at": stale_time,
        "_node_content": json.dumps({"text": stale_text}),
        "_node_type": "TextNode"
    }
    fresh_meta = {
        "clause_id": "C_FRESH",
        "clause_type": "Limit",
        "score": 0.90,
        "last_accessed_at": fresh_time,
        "_node_content": json.dumps({"text": fresh_text}),
        "_node_type": "TextNode"
    }

    # Add docs for each test run (ensures fresh state)
    memory.add_memory(stale_text, stale_meta)
    memory.add_memory(fresh_text, fresh_meta)

    if mode == "hybrid":
        results = memory.get_relevant("What is the transfer limit?", top_k=2, rescore=True)
        assert len(results) == 2
        hybrid_scores = [doc.metadata["hybrid_score"] for doc in results]
        clause_ids = [doc.metadata["clause_id"] for doc in results]
        print(f"[Hybrid] Hybrid scores: {hybrid_scores}, Clause IDs: {clause_ids}")
        assert clause_ids[0] == "C_FRESH"
        assert hybrid_scores[0] > hybrid_scores[1]

    elif mode == "decay":
        results = memory.get_relevant("What is the transfer limit?", top_k=2, apply_decay=True, rescore=False)
        assert len(results) == 2
        decay_scores = [memory.scorer.score(doc.metadata) for doc in results]
        clause_ids = [doc.metadata["clause_id"] for doc in results]
        print(f"[Decay] Decay scores: {decay_scores}, Clause IDs: {clause_ids}")
        assert clause_ids[0] == "C_FRESH"
        assert decay_scores[0] > decay_scores[1]

    # in default the similarity search does not take the 'score' metadata into account it ranks based on what the embedding similarity found more relevant
    elif mode == "default":
        results = memory.get_relevant("What is the transfer limit?", top_k=2, apply_decay=False, rescore=False)
        assert len(results) == 2
        sim_scores = [doc.metadata["score"] for doc in results]
        clause_ids = [doc.metadata["clause_id"] for doc in results]
        print(f"[Default] Similarity scores: {sim_scores}, Clause IDs: {clause_ids}")
        # The order is determined by embedding similarity, not your manual score!
        # Just check both docs are present
        assert set(clause_ids) == {"C_FRESH", "C_STALE"}

