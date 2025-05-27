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
from utils.logger import get_logger
from memory.langchain_retriever import GraphMemoryRetriever
from faker import Faker

from llama_index.core.schema import Document
from memory.llamaindex_retriever import get_llamaindex_query_engine_from_docs

logger = get_logger("jsentrix")

@pytest.fixture(scope="module")
def langchain_retriever():
    return GraphMemoryRetriever()

@pytest.fixture(scope="module")
def faker():
    return Faker()

def build_compliance_query(transaction):
    return f"""
    Analyze this transaction for compliance violations.
    Transaction details:{transaction}
    First, identify relevant compliance clauses.
    Then explain if any violations exist.
    Final answer must be: YES or NO followed by a brief explanation.
    """

def test_jsentrix_rag_pipeline(langchain_retriever, faker):
    from utils.neo4j_utils import get_neo4j_config
    # Should only log once per test run
    logger.info("Neo4j config (should cache): %s", get_neo4j_config())

    # 1. Intentionally violating transaction (C2)
    violating_transaction = {
        "amount": "$12,000.00",
        "sender": "SANCTIONED_ENTITY_X",   # This should match C2
        "receiver": "GB00FAKE12345678901234",
        "currency": "USD",
        "timestamp": "2025-05-24T10:00:00"
    }
    # 2. Three normal transactions
    normal_transactions = [{
        "amount": faker.pricetag(),
        "sender": faker.swift11(),
        "receiver": faker.iban(),
        "currency": faker.currency_code(),
        "timestamp": faker.iso8601()
    } for _ in range(3)]

    transactions = [violating_transaction] + normal_transactions

    for idx, txn in enumerate(transactions):
        logger.info(f"\n === Processing Transaction {idx+1} ===")
        logger.info(f"Transaction: {txn}")

        # ---1. LangChain hybrid retrieval ---
        raw_query = f"Compliance check for {txn['currency']} transfer from {txn['sender']} to {txn['receiver']}"
        langchain_docs = langchain_retriever.get_relevant(raw_query, top_k=5, rescore=True)
        assert langchain_docs, "Langchain retrieval failed"

        logger.info(f"[LangChain] Retrieved {len(langchain_docs)} documents:")
        for doc in langchain_docs:
            logger.info(f"💫 {doc.metadata.get('clause_id')} | Hybrid: {doc.metadata['hybrid_score']:.2f}")

        # ---2. Build dynamic metadata mapping for injection ---
        dynamic_metadata_by_clause_id = {
            doc.metadata["clause_id"]: dict(doc.metadata)
            for doc in langchain_docs
        }

        # ---3. Convert LangChain docs to LlamaIndex docs ---
        llamaindex_docs = [
            Document(
                text=doc.page_content,
                metadata=doc.metadata
            )
            for doc in langchain_docs
        ]

        # ---4. Create a LlamaIndex query engine from these docs with postprocessors and reward logic ---
        query_engine = get_llamaindex_query_engine_from_docs(
            llamaindex_docs,
            dynamic_metadata_by_clause_id=dynamic_metadata_by_clause_id
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
        logger.info(getattr(response, 'response', response))
        logger.info(f"LLM Answer for Transaction {idx+1}: {str(response)}")

        # ---6. Compliance assertions ---
        if idx == 0:
            # The first transaction should be a violation (YES)
            assert "YES" in str(response).upper(), "LLM failed to detect compliance violation for transaction 1"
        else:
            # The rest should be NO
            assert "NO" in str(response).upper(), f"LLM incorrectly detected violation for transaction {idx+1}"

        # ---7. Verify metadata propagation ---
        for node in getattr(response, 'source_nodes', []):
            print("Node metadata after all postprocessors:", node.metadata)
            assert "hybrid_score" in node.metadata, "Hybrid score missing in node metadata"
            assert "clause_id" in node.metadata, "Clause ID missing in node metadata"
            assert "summary" in node.metadata, "Summary missing in node metadata"
            assert isinstance(node.metadata["summary"], str) and node.metadata["summary"].strip(), "Summary is empty or not a string"
        
        # ---8. Postprocessor scoring checks ---
        # Interpret the Scores
        # score / sim_core: Original similarity or relevance score from retrieval.
        # decayed_score: Score after applying any time-based or usage-based decay.
        # hybrid_score: Final score used for reranking; typically incorporates both similarity and decay.
        # Order of nodes: Nodes with higher hybrid scores are ranked higher and passed to the LLM.
        for node in getattr(response, 'source_nodes', []):
            meta = node.metadata
            original_score = meta.get('sim_core', meta.get('score'))
            logger.info(f"Node {meta.get('clause_id')} scores: "
                        f"original_score={original_score}, "
                        f"score={meta.get('score')}, "
                        f"decayed_score={meta.get('decayed_score')}, "
                        f"hybrid_score={meta.get('hybrid_score')}")
            # Assert all scores are present and are floats
            assert isinstance(original_score, (float, int)), "original_score missing or not a number"
            assert isinstance(meta.get('decayed_score'), (float, int)), "decayed_score missing or not a number"
            assert isinstance(meta.get('hybrid_score'), (float, int)), "hybrid_score missing or not a number"
            # Assert hybrid_score is less than or equal to original score (decay/rerank applied)
            assert meta['hybrid_score'] <= original_score, "hybrid_score should be <= original score"
            # Assert decayed_score is less than or equal to original score
            assert meta['decayed_score'] <= original_score, "decayed_score should be <= original score"

        # ---9. (Optional) Check reranking order ---
        hybrid_scores = [node.metadata['hybrid_score'] for node in getattr(response, 'source_nodes', [])]
        logger.info(f"Hybrid scores order: {hybrid_scores}")
        # expect reranking, check that scores are in descending order
        assert hybrid_scores == sorted(hybrid_scores, reverse=True), "Nodes not reranked by hybrid_score"

        logger.info(f" === End Transaction {idx+1} Processing ===\n")
