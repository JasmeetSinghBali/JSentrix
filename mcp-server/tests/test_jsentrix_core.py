# pytest tests/test_jsentrix_core.py -v -s --log-cli-level=INFO
import pytest
from utils.logger import get_logger
from memory.langchain_retriever import GraphMemoryRetriever
from memory.llamaindex_retriever import get_llamaindex_query_engine
from faker import Faker

logger = get_logger(__name__)

@pytest.fixture(scope="module")
def langchain_retriever():
    return GraphMemoryRetriever()

@pytest.fixture(scope="module")
def llamaindex_query_engine():
    engine = get_llamaindex_query_engine()
    assert engine is not None, "Failed to initialize LlamaIndex query engine"
    return engine

# https://github.com/joke2k/faker
@pytest.fixture(scope="module")
def faker():
    return Faker()

def build_compliance_query(transaction):
    return f"""
    Analyze this transaction for compliance voilations.
    Transaction details:{transaction}
    First, identify relevant compliance clauses.
    Then explain if any violations exist.
    Final answer must be: YES or NO followed by a brief explanation.
    """

def test_jsentrix_rag_pipeline(langchain_retriever,llamaindex_query_engine,faker):
    # 3 mock banking transactions generated
    transactions=[{
        "amount": faker.pricetag(),
        "sender": faker.swift11(),
        "receiver": faker.iban(),
        "currency": faker.currency_code(),
        "timestamp": faker.iso8601()
    }for _ in range(3)]

    for idx,txn in enumerate(transactions):
        logger.info(f"\n === Processing Transaction {idx+1} ===")
        logger.info(f"Transaction: {txn}")

        # ---1. langchain hybrid retrieval ---
        raw_query=f"Compliance check for {txn["currency"]} transfer from {txn["sender"]} to {txn["receiver"]}"
        langchain_docs=langchain_retriever.get_relevant(raw_query,top_k=5,rescore=True)
        assert langchain_docs,"Langchain retrieval failed"

        # langchain results
        logger.info(f"[LangChain] Retrieved {len(langchain_docs)} documents:")
        for doc in langchain_docs:
            logger.info(f"💫 {doc.metadata.get("clause_id")}| Hybrid: {doc.metadata["hybrid_score"]}:.2f")

        # --- 2. llamaIndex processing & llm analysis ---
        structured_query = build_compliance_query(txn)
        response=llamaindex_query_engine.query(structured_query)

        # log full pipeline results
        logger.info(f"\n[LlamaIndex] Response Metadata:")
        logger.info(f"- Score: {response.metadata.get('score')}")
        logger.info(f"- Hybrid Score: {response.metadata.get('hybrid_score')}")
        logger.info(f"- Retrieved Nodes: {len(response.source_nodes)}")
        
        logger.info("\n[LLM Analysis]")
        logger.info(response.response)

        # ---3. compliance assertions ---
        assert "YES" in response.response.upper() or "NO" in response.response.upper(), \
        "LLM failed to provide YES/NO compliance decision" 

        # ---4. verify metadata propagation ---
        for node in response.source_nodes:
            assert "hybrid_score" in node.metadata, "Hybrid score missing in node metadata"
            assert "clause_id" in node.metadata, "Clause ID missing in node metadata"

        logger.info(f" === End Transaction {idx+1} Processing ===\n")
