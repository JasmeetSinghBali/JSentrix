# pytest .\tests\test_jsentrix_core.py -v -s --log-cli-level=INFO
import pytest
from utils.logger import get_logger
from memory.langchain_retriever import GraphMemoryRetriever
from faker import Faker

from llama_index.core.schema import Document
from memory.llamaindex_retriever import get_llamaindex_query_engine_from_docs

logger = get_logger(__name__)

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
    transactions = [{
        "amount": faker.pricetag(),
        "sender": faker.swift11(),
        "receiver": faker.iban(),
        "currency": faker.currency_code(),
        "timestamp": faker.iso8601()
    } for _ in range(3)]

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

        # ---6. Compliance assertions ---
        assert "YES" in str(response).upper() or "NO" in str(response).upper(), \
            "LLM failed to provide YES/NO compliance decision"

        # ---7. Verify metadata propagation ---
        for node in getattr(response, 'source_nodes', []):
            print("Node metadata after all postprocessors:", node.metadata)
            assert "hybrid_score" in node.metadata, "Hybrid score missing in node metadata"
            assert "clause_id" in node.metadata, "Clause ID missing in node metadata"

        logger.info(f" === End Transaction {idx+1} Processing ===\n")
