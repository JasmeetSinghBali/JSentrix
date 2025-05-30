# pytest .\tests\test_jsentrix_core.py -v -s --log-cli-level=INFO for general info logs
# USE FOR:
# Most test runs
# Seeing important info, warnings, and errors
# Verifying that your pipeline works end-to-end
# Confirming compliance detection, score propagation, and general flow

# pytest .\tests\test_jsentrix_core.py -v -s --log-cli-level=DEBUG for cache check
# USE FOR
# Diagnosing issues with config caching, connection pooling, or postprocessor logic
# Verifying that your Neo4j config and driver are only initialized once
# Inspecting detailed step-by-step flow, variable values, and all debug logs
# Verifying scoring, decay, reranking, caching
import pytest
from faker import Faker
from utils.logger import get_logger

# Update these imports to match your new structure!
from application.retrievers.langchain_retriever import GraphMemoryRetriever
from application.retrievers.llamaindex_retriever import (
    get_llamaindex_query_engine_from_docs,
)
from llama_index.core.schema import Document
from utils.neo4j_utils import get_neo4j_config

from domain.models import MemoryEvent
from infrastructure.memory_event_repository import MemoryEventRepository
from application.retrievers.memory_event_retriever import MemoryEventRetriever
from utils.embedding_utils import get_langchain_embedding_model

logger = get_logger("jsentrix")


@pytest.fixture(scope="module")
def langchain_retriever():
    return GraphMemoryRetriever()


@pytest.fixture(scope="module")
def faker():
    return Faker()


@pytest.fixture(scope="module")
def memory_event_repository():
    return MemoryEventRepository()


@pytest.fixture(scope="module")
def memory_event_retriever(memory_event_repository):
    return MemoryEventRetriever(memory_event_repository)


@pytest.fixture(scope="module")
def embedding_model():
    return get_langchain_embedding_model()


def build_compliance_query(transaction):
    return f"""
    Analyze this transaction for compliance violations.
    Transaction details:{transaction}
    First, identify relevant compliance clauses.
    Then explain if any violations exist.
    Final answer must be: YES or NO followed by a brief explanation.
    """


# test-core-1: Rag pipeline
def test_jsentrix_rag_pipeline(langchain_retriever, faker):
    logger.info("Neo4j config (should cache): %s", get_neo4j_config())

    # 1. Intentionally violating transaction (C2)
    violating_transaction = {
        "amount": "$12,000.00",
        "sender": "SANCTIONED_ENTITY_X",  # This should match C2
        "receiver": "GB00FAKE12345678901234",
        "currency": "USD",
        "timestamp": "2025-05-24T10:00:00",
    }
    # 2. Three normal transactions
    normal_transactions = [
        {
            "amount": faker.pricetag(),
            "sender": faker.swift11(),
            "receiver": faker.iban(),
            "currency": faker.currency_code(),
            "timestamp": faker.iso8601(),
        }
        for _ in range(3)
    ]

    transactions = [violating_transaction] + normal_transactions

    for idx, txn in enumerate(transactions):
        logger.info(f"\n === Processing Transaction {idx+1} ===")
        logger.info(f"Transaction: {txn}")

        # ---1. LangChain hybrid retrieval ---
        raw_query = f"Compliance check for {txn['currency']} transfer from {txn['sender']} to {txn['receiver']}"
        langchain_docs = langchain_retriever.get_relevant(
            raw_query, top_k=5, rescore=True
        )
        assert langchain_docs, "Langchain retrieval failed"

        logger.info(f"[LangChain] Retrieved {len(langchain_docs)} documents:")
        for doc in langchain_docs:
            logger.info(
                f"💫 {doc.metadata.get('clause_id')} | Hybrid: {doc.metadata.get('hybrid_score', 0):.2f}"
            )

        # ---2. Build dynamic metadata mapping for injection ---
        dynamic_metadata_by_clause_id = {
            doc.metadata["clause_id"]: dict(doc.metadata) for doc in langchain_docs
        }

        # ---3. Convert LangChain docs to LlamaIndex docs ---
        llamaindex_docs = [
            Document(text=doc.page_content, metadata=doc.metadata)
            for doc in langchain_docs
        ]

        # ---4. Create a LlamaIndex query engine from these docs with postprocessors and reward logic ---
        query_engine = get_llamaindex_query_engine_from_docs(
            llamaindex_docs, dynamic_metadata_by_clause_id=dynamic_metadata_by_clause_id
        )

        # ---5. LlamaIndex processing & LLM analysis ---
        structured_query = build_compliance_query(txn)
        response = query_engine.query(structured_query)

        logger.info(f"\n[LlamaIndex] Response Metadata:")
        if response is None:
            logger.error("LlamaIndex query returned None!")
            continue

        logger.info(f"- Retrieved Nodes: {len(getattr(response, 'source_nodes', []))}")
        logger.info("\n[LLM Analysis]")
        logger.info(getattr(response, "response", response))
        logger.info(f"LLM Answer for Transaction {idx+1}: {str(response)}")

        # ---6. Compliance assertions ---
        if idx == 0:
            # The first transaction should be a violation (YES)
            assert (
                "YES" in str(response).upper()
            ), "LLM failed to detect compliance violation for transaction 1"
        else:
            # The rest should be NO
            assert (
                "NO" in str(response).upper()
            ), f"LLM incorrectly detected violation for transaction {idx+1}"

        # ---7. Verify metadata propagation ---
        for node in getattr(response, "source_nodes", []):
            logger.info(f"Node metadata after all postprocessors: {node.metadata}")
            assert (
                "hybrid_score" in node.metadata
            ), "Hybrid score missing in node metadata"
            assert "clause_id" in node.metadata, "Clause ID missing in node metadata"
            assert "summary" in node.metadata, "Summary missing in node metadata"
            assert (
                isinstance(node.metadata["summary"], str)
                and node.metadata["summary"].strip()
            ), "Summary is empty or not a string"

        # ---8. Postprocessor scoring checks ---
        for node in getattr(response, "source_nodes", []):
            meta = node.metadata
            original_score = meta.get("sim_score", meta.get("score"))
            logger.info(
                f"Node {meta.get('clause_id')} scores: "
                f"original_score={original_score}, "
                f"score={meta.get('score')}, "
                f"decayed_score={meta.get('decayed_score')}, "
                f"hybrid_score={meta.get('hybrid_score')}"
            )
            # Assert all scores are present and are floats
            assert isinstance(
                original_score, (float, int)
            ), "original_score missing or not a number"
            assert isinstance(
                meta.get("decayed_score"), (float, int)
            ), "decayed_score missing or not a number"
            assert isinstance(
                meta.get("hybrid_score"), (float, int)
            ), "hybrid_score missing or not a number"
            # Assert hybrid_score is less than or equal to original score (decay/rerank applied)
            assert (
                meta["hybrid_score"] <= original_score
            ), "hybrid_score should be <= original score"
            # Assert decayed_score is less than or equal to original score
            assert (
                meta["decayed_score"] <= original_score
            ), "decayed_score should be <= original score"

        # ---9. (Optional) Check reranking order ---
        hybrid_scores = [
            node.metadata["hybrid_score"]
            for node in getattr(response, "source_nodes", [])
        ]
        logger.info(f"Hybrid scores order: {hybrid_scores}")
        assert hybrid_scores == sorted(
            hybrid_scores, reverse=True
        ), "Nodes not reranked by hybrid_score"

        logger.info(f" === End Transaction {idx+1} Processing ===\n")


# test-core-2: Memory-aware triage flow
# Run only the new memory-aware test
# pytest ./tests/test_jsentrix_core.py -v -s -k test_memory_aware_triage_flow
def test_memory_aware_triage_flow(
    langchain_retriever,
    memory_event_repository,
    memory_event_retriever,
    embedding_model,
    faker,
):
    """
    Simulates a triage flow where past memory events influence current transactions.
    """
    logger.info("\n === Testing Memory-Aware Triage Flow ===")

    # 1. Store mock memory events from previous transactions
    mock_events = [
        {
            "prompt": "Compliance check for USD transfer from SANCTIONED_ENTITY_X to GB00FAKE12345678901234",
            "llm_response": "YES - Sanctioned entity detected.",
            "scores": {"risk_score": 0.95},
            "user_id": "audit_user_1",
        },
        {
            "prompt": "Compliance check for EUR transfer from BANK_A to BANK_B",
            "llm_response": "NO - No violations found.",
            "scores": {"risk_score": 0.15},
            "user_id": "audit_user_2",
        },
    ]

    for event_data in mock_events:
        event = MemoryEvent(
            agent_name="TestAgent",
            prompt=event_data["prompt"],
            llm_response=event_data["llm_response"],
            scores=event_data["scores"],
            user_id=event_data["user_id"],
        )
        # Generate embedding from prompt
        vector = embedding_model.embed_query(event.prompt)
        memory_event_repository.store(event, vector)

    # 2. Simulate a new transaction similar to a high-risk past event
    new_transaction = {
        "amount": "$15,000.00",
        "sender": "SANCTIONED_ENTITY_X",  # Similar to stored high-risk event
        "receiver": "GB00FAKE12345678901234",
        "currency": "USD",
        "timestamp": "2025-05-30T12:00:00",
    }
    new_prompt = f"Compliance check for {new_transaction['currency']} transfer from {new_transaction['sender']} to {new_transaction['receiver']}"

    # 3. Retrieve relevant memories using vector + metadata
    query_vector = embedding_model.embed_query(new_prompt)
    relevant_memories, _ = memory_event_retriever.get_events(
        query_vector=query_vector,
        filters={
            "user_id": "audit_user_1"
        },  # this will be known from the session , login or request context this can be omitted to take leverage of all past high-risk memory events regardless of user
        top_k=2,
    )

    logger.info(f"\n[Memory-Aware Triage] Retrieved {len(relevant_memories)} memories:")
    for memory in relevant_memories:
        logger.info(f"📝 Memory: {memory.prompt} | Risk: {memory.scores['risk_score']}")

    # 4. Assert high-risk memory is prioritized
    assert len(relevant_memories) > 0, "No memories retrieved"
    assert any(
        "SANCTIONED_ENTITY_X" in memory.prompt and memory.scores["risk_score"] > 0.9
        for memory in relevant_memories
    ), "High-risk memory not retrieved"

    # 5. (Optional) Simulate injecting memories into LLM context
    # This would depend on agent implementation
    logger.info("\n[Simulated LLM Context Injection]")
    context = "\n".join(
        [f"Past decision: {memory.llm_response}" for memory in relevant_memories]
    )
    logger.info(f"Context:\n{context}")

    # 6. Verify context influences analysis (simplified assertion)
    assert "YES" in context, "High-risk context not injected"

    # 7. Fetch all events for the user using pagination and assert correctness
    all_events = memory_event_repository.fetch_all_events_with_pagination(
        filters={"user_id": "audit_user_1"}, batch_size=10
    )
    logger.info(
        f"\n[Pagination Fetch] Retrieved {len(all_events)} events for user 'audit_user_1'"
    )
    assert (
        len(all_events) >= 1
    ), "No events found for user 'audit_user_1' with pagination fetch"
    assert any(
        "SANCTIONED_ENTITY_X" in event.prompt and event.scores["risk_score"] > 0.9
        for event in all_events
    ), "High-risk event not found in paginated fetch"

    # 8. Fetch all events for all users (no filter) and assert both events are present
    all_events_unfiltered = memory_event_repository.fetch_all_events_with_pagination(
        filters=None, batch_size=10
    )
    logger.info(
        f"\n[Pagination Fetch] Retrieved {len(all_events_unfiltered)} events (unfiltered)"
    )
    prompts = [event.prompt for event in all_events_unfiltered]
    assert any(
        "SANCTIONED_ENTITY_X" in prompt for prompt in prompts
    ), "High-risk event missing in all-events fetch"
    assert any(
        "BANK_A" in prompt for prompt in prompts
    ), "Low-risk event missing in all-events fetch"
