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
import asyncio
from faker import Faker
from utils.logger import get_logger

# Update these imports to match your new structure!
from application.retrievers.langchain_retriever import GraphMemoryRetriever
from application.retrievers.llamaindex_retriever import (
    get_llamaindex_query_engine_from_docs,
)
from llama_index.llms.ollama import Ollama
from llama_index.core.schema import Document as LlamaIndexDocument
from langchain_core.documents import Document as LangChainDocument
from utils.neo4j_utils import get_neo4j_config
from utils.summarizer import T5Summarizer

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
    Final answer must be: YES, NO or ND where ND stands for non-deterministic followed by a brief explanation.
    """


# test-core-1: Rag pipeline
# pytest ./tests/test_jsentrix_core.py -v -s -k test_jsentrix_rag_pipeline
def test_jsentrix_rag_pipeline(langchain_retriever, faker):
    """
    Run the RAG pipeline test
        - Qwen3:1.7B makes the compliance decision.
        - Gemma3:1b generates a summary/report based on Qwen's output.

    Requirements:
        - Neo4j database running and accessible.
        - ingestion run_pipeline completed.
        - ollama qwen3:1.7b and gemma3:1b running locally.
        - No MCP server or gateway or mcp-client required.
        - Recommended: Run with a clean or test-specific Neo4j instance to avoid data contamination.
    """
    logger.info("Running RAG pipeline test with model: qwen3:1.7b")
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
        logger.info(f"\n === Processing Transaction {idx+1} with model qwen3:1.7b ===")
        logger.info(f"Transaction: {txn}")

        # ---1. LangChain hybrid retrieval ---
        raw_query = f"Compliance check for {txn['currency']} transfer from {txn['sender']} to {txn['receiver']}"
        langchain_docs = langchain_retriever.get_relevant(
            raw_query, top_k=5, rescore=True
        )
        assert langchain_docs, "Langchain retrieval failed"

        # 📌 Inject a mock prior_event document manually to check the source "prior_event" skips decay for it
        prior_event_doc = LangChainDocument(
            page_content="Previous flagged transaction involving the same sender",
            metadata={
                "clause_id": "prior_event_001",
                "summary": "Prior violation on same entity",
                "sim_score": 0.95,
                "score": 0.95,
                "source": "prior_event",
                "hybrid_score": 0.95,
            },
        )
        langchain_docs.append(prior_event_doc)

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
            LlamaIndexDocument(text=doc.page_content, metadata=doc.metadata)
            for doc in langchain_docs
        ]

        # ---4. Create a LlamaIndex query engine with specified model ---
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

        # 📌 step 6 to 9 can be done by a judge agent which uses some other model for inference also generate a structured dict that contains
        # 🎈 Judge agent shud form strucutre data and have 2nd level inference with diff model
        # Risk score
        # Violations
        # Recommendations
        # Source metadata
        # as
        # return JudgeOutput(
        #     analysis="Analysis failed",
        #     risk_score=100,
        #     violations=["COMPLIANCE_CHECK_FAILED"],
        #     recommendations=["Review manually"],
        #     metadata={"error": str(e)},
        #     judge_id=f"err-{uuid.uuid4()}"
        # )
        # the above JudgeOutput will be passed to the summarizer finally to create a report and bg worker that sends that to the ui for now via forward event/ here it could be passed to concerned superadmin/admin, bank staff emails also
        # ---6. Compliance assertions ---
        if idx == 0:
            assert (
                "YES" in str(response).upper()
            ), f"Qwen3:1.7B failed to detect compliance violation for transaction 1"
        else:
            assert (
                "NO" in str(response).upper()
            ), f"Qwen3:1.7B incorrectly detected violation for transaction {idx+1}"

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
            assert isinstance(
                original_score, (float, int)
            ), "original_score missing or not a number"
            assert isinstance(
                meta.get("decayed_score"), (float, int)
            ), "decayed_score missing or not a number"
            assert isinstance(
                meta.get("hybrid_score"), (float, int)
            ), "hybrid_score missing or not a number"

            if meta.get("source", "clause") == "prior_event":
                logger.debug(f"Skipping score assertions for prior_event node: {meta}")
                assert (
                    meta["decayed_score"] == original_score
                ), "Prior_event decayed_score should equal original"
                assert (
                    node.score == original_score
                ), "Node score should equal original for prior_event"
            else:
                assert (
                    meta["decayed_score"] <= original_score
                ), "decayed_score should be <= original score"
                assert (
                    meta["hybrid_score"] <= original_score
                ), "hybrid_score should be <= original score"

        # ---9. (Optional) Check reranking order ---
        hybrid_scores = [
            node.metadata["hybrid_score"]
            for node in getattr(response, "source_nodes", [])
        ]
        logger.info(f"Hybrid scores order: {hybrid_scores}")
        assert hybrid_scores == sorted(
            hybrid_scores, reverse=True
        ), "Nodes not reranked by hybrid_score"

        # ---10. Summary/report with Gemma3:1b ---
        summary_prompt = (
            f"Summarize this compliance decision for auditors and end users:\n"
            f"Transaction: {txn}\n"
            f"Decision: {str(response)}"
        )
        # Use Gemma3:1b for summary
        summary_llm = Ollama(model="gemma3:1b")
        summary = summary_llm.complete(prompt=summary_prompt).text
        logger.info(f"[Gemma3:1b Summary] {summary}")
        assert (
            summary and isinstance(summary, str) and len(summary.strip()) > 0
        ), "Gemma3:1b returned empty summary"

        logger.info(f" === End Transaction {idx+1} Processing ===\n")


# test-core 2
# Run only the new memory-aware test_core_2_async_end_to_end triage flow
# pytest ./tests/test_jsentrix_core.py -v -s -k test_core_2_async_end_to_end
@pytest.mark.asyncio
async def test_core_2_async_end_to_end(
    langchain_retriever,
    memory_event_repository,
    memory_event_retriever,
    embedding_model,
    faker,
):
    """
    Simulates a triage flow where past memory events influence current transactions.

    End-to-end async test: memory event storage, retrieval, summarizer, and hybrid retrieval pipeline.
    Uses unique mock values to ensure independence from other tests.

    Requirements:
        - neo4j shud be running and run_pipeline for prep knowledge base
        - qdrant shud be running then run qdrant_setup.py
        - No need to run the MCP server or gateway; this test interacts directly with repository, retriever, and summarizer APIs.
        - All test data is unique and isolated for this test.
        - If using an embedding model or summarizer that requires external files or network, ensure these are available.
        - Python environment must support asyncio and pytest-asyncio (install with `pip install pytest-asyncio`).
    """
    logger.info("\n === [ASYNC] End-to-End Async Pipeline Test ===")

    # 1. Store mock memory events asynchronously (distinct from other tests)
    summarizer = T5Summarizer()
    mock_events = [
        {
            "prompt": "Async compliance audit for SGD transfer from ASYNC_CORP_42 to SG00ASYNC555888777",
            "llm_response": "YES - Async anomaly detected.",
            "scores": {"risk_score": 0.93},
            "user_id": "async_unique_user_42",
        },
        {
            "prompt": "Async compliance audit for JPY transfer from ASYNC_BANK_Z to ASYNC_BANK_Y",
            "llm_response": "NO - All clear.",
            "scores": {"risk_score": 0.18},
            "user_id": "async_unique_user_99",
        },
    ]

    for event_data in mock_events:
        # Simulate a minimal original transaction for testing
        mock_txn = {
            "txn_id": f"txn_{event_data['user_id']}",
            "amount": 10000 if "YES" in event_data["llm_response"] else 1000,
            "sender": event_data["prompt"].split("from ")[1].split(" to ")[0],
            "receiver": event_data["prompt"].split("to ")[1],
            "currency": event_data["prompt"].split("for ")[1].split(" transfer")[0],
            "timestamp": "2025-06-02T09:00:00",
        }
        event = MemoryEvent(
            agent_name="AsyncUniqueAgent",
            prompt=event_data["prompt"],
            llm_response=event_data["llm_response"],
            decision="YES" if "YES" in event_data["llm_response"] else "NO",
            original_transaction=mock_txn,
            user_id=event_data["user_id"],
            relevant_clause_ids=[],  # or fill if you want
            metadata={
                "risk_score": event_data["scores"]["risk_score"],
                "test_case": True,
            },
            extra_context={},
            summary=None,
        )
        event.summary = await summarizer.async_summarize(event.prompt)
        vector = await asyncio.get_running_loop().run_in_executor(
            None, embedding_model.embed_query, event.prompt
        )
        await memory_event_repository.store(event, vector)

    # 2. Simulate a new transaction with unique values
    new_transaction = {
        "amount": 10000,
        "sender": "ASYNC_CORP_42",
        "receiver": "SG00ASYNC555888777",
        "currency": "SGD",
        "timestamp": "2025-06-02T09:00:00",
    }
    new_prompt = f"Async compliance audit for {new_transaction['currency']} transfer from {new_transaction['sender']} to {new_transaction['receiver']}"

    # 3. Retrieve relevant memories using vector + metadata (async)
    query_vector = await asyncio.get_running_loop().run_in_executor(
        None, embedding_model.embed_query, new_prompt
    )
    # Add sender, amount, and (optionally) clause_hits to filters
    filters = {
        "user_id": "async_unique_user_42",
        "original_transaction.sender": new_transaction["sender"],
        "original_transaction.amount": new_transaction["amount"],
        # Optionally add clause hits if available
        # "relevant_clause_ids": ["your_clause_id"]
    }
    relevant_memories = await memory_event_retriever.async_get_events(
        query_vector=query_vector,
        filters=filters,
        top_k=5,
    )

    def is_strong_match(memory, txn, clause_hits=None):
        if memory.original_transaction["sender"] != txn["sender"]:
            return False
        if str(memory.original_transaction["amount"]) != str(txn["amount"]):
            return False
        if clause_hits is not None:
            if not set(clause_hits).issubset(set(memory.relevant_clause_ids)):
                return False
        return True

    clause_hits = []  # Fill as needed
    matching_event = next(
        (
            m
            for m in relevant_memories
            if is_strong_match(m, new_transaction, clause_hits)
        ),
        None,
    )

    if matching_event:
        logger.info(
            f"✅ Cache hit, returning stored decision: {matching_event.decision}"
        )
        result = {
            "decision": matching_event.decision,
            "llm_response": matching_event.llm_response,
            "cached-events-result": True,
            "memory_event_id": matching_event.event_id,
            "original_transaction": matching_event.original_transaction,
            "metadata": matching_event.metadata,
            "summary": matching_event.summary,
        }
        # --- Add assertions for the cache hit result ---
        assert result["cached-events-result"] is True
        assert result["decision"] == "YES"
        assert result["original_transaction"]["sender"] == new_transaction["sender"]
        assert result["original_transaction"]["receiver"] == new_transaction["receiver"]
        # You can add more assertions as needed
    else:
        logger.info("No cache hit, run full analysis...")

    logger.info(
        f"\n[ASYNC Memory-Aware Triage] Retrieved {len(relevant_memories)} memories:"
    )
    for memory in relevant_memories:
        logger.info(
            f"📝 Memory: {memory.prompt} | Risk: {memory.metadata["risk_score"]}"
        )

    # Assert high-risk memory is prioritized
    assert len(relevant_memories) > 0, "No memories retrieved"
    assert any(
        "ASYNC_CORP_42" in memory.prompt and memory.metadata["risk_score"] > 0.9
        for memory in relevant_memories
    ), "High-risk async memory not retrieved"

    # 4. Simulate injecting memories into LLM context (async summarizer)
    logger.info("\n[ASYNC Simulated LLM Context Injection]")
    context = "\n".join(
        [f"Past decision: {memory.llm_response}" for memory in relevant_memories]
    )
    logger.info(f"Context:\n{context}")
    assert "YES" in context, "High-risk context not injected"

    # 5. Fetch all events for the user using async pagination and assert correctness
    all_events = await memory_event_repository.fetch_all_events_with_pagination(
        filters={"user_id": "async_unique_user_42"}, batch_size=10
    )
    logger.info(
        f"\n[ASYNC Pagination Fetch] Retrieved {len(all_events)} events for user 'async_unique_user_42'"
    )
    assert (
        len(all_events) >= 1
    ), "No events found for user 'async_unique_user_42' with async pagination fetch"
    assert any(
        "ASYNC_CORP_42" in event.prompt and event.metadata["risk_score"] > 0.9
        for event in all_events
    ), "High-risk async event not found in paginated fetch"

    # 6. Fetch all events for all users (no filter) and assert both events are present
    all_events_unfiltered = (
        await memory_event_repository.fetch_all_events_with_pagination(
            filters=None, batch_size=10
        )
    )
    logger.info(
        f"\n[ASYNC Pagination Fetch] Retrieved {len(all_events_unfiltered)} events (unfiltered)"
    )
    prompts = [event.prompt for event in all_events_unfiltered]
    assert any(
        "ASYNC_CORP_42" in prompt for prompt in prompts
    ), "High-risk async event missing in all-events fetch"
    assert any(
        "ASYNC_BANK_Z" in prompt for prompt in prompts
    ), "Low-risk async event missing in all-events fetch"

    logger.info("=== [ASYNC] End-to-End Async Pipeline Test PASSED ===\n")
