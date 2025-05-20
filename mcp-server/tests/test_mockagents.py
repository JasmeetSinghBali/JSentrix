import pytest
import json
from memory.langchain_retriever import GraphMemoryRetriever
from utils.neo4j_cypher_utils import (
    get_related_clauses,
    get_clause_details,
    get_clauses_by_type,
)
from memory.llamaindex_retriever import get_llamaindex_query_engine

# ----------- LangChain Agent ------------

class MockLangChainAgent:
    """
    LangChain mock agent: Only retrieves, does not use an LLM for synthesis.
    """
    def __init__(self, memory):
        self.memory = memory

    def run(self, query, filter_metadata=None):
        results = self.memory.get_relevant(query, filter_metadata=filter_metadata)
        return results

@pytest.fixture
def memory():
    return GraphMemoryRetriever()

def test_langchain_agent_basic(memory):
    # Add mock memory with LlamaIndex-compatible metadata
    text = "The transfer limit is $10,000 per month."
    metadata = {
        "clause_type": "Limit",
        "clause_id": "C100",
        "title": "Transfer Limit",
        "_node_content": json.dumps({"text": text}),
        "_node_type": "TextNode"
    }
    memory.add_memory(text, metadata)
    agent = MockLangChainAgent(memory=memory)
    results = agent.run("What is the transfer limit?")
    assert any("10,000" in doc.page_content for doc in results)

def test_langchain_agent_filtering(memory):
    # Add another clause of a different type
    memory.add_memory("No transactions allowed.", {
        "clause_type": "Prohibition",
        "clause_id": "C101",
        "title": "Prohibited Transactions",
        "_node_content": json.dumps({"text": "No transactions allowed."}),
        "_node_type": "TextNode"
    })
    agent = MockLangChainAgent(memory=memory)
    # Should only get Limit type
    results = agent.run("What is the transfer limit?", filter_metadata={"clause_type": "Limit"})
    assert all(doc.metadata.get("clause_type") == "Limit" for doc in results)

def test_langchain_agent_graph_context(memory):
    # Test graph context via cypher utils for the mock clause
    details = get_clause_details("C100")
    assert details and details[0]["c"]["clause_id"] == "C100"
    # No relationships for this mock, but function should work
    rels = get_related_clauses("C100", rel_type="REFERENCES", direction="out")
    assert isinstance(rels, list)

# ----------- LlamaIndex Agent ------------

class MockLlamaIndexAgent:
    """
    LlamaIndex mock agent: Retrieves, then uses an LLM to generate the final answer.
    """
    def __init__(self, query_engine):
        self.query_engine = query_engine

    def run(self, query):
        response = self.query_engine.query(query)
        # LlamaIndex returns a Response object; .response is the synthesized answer
        return str(response)

@pytest.fixture(scope="module")
def query_engine():
    engine = get_llamaindex_query_engine()
    if engine is None:
        pytest.skip("LlamaIndex query engine could not be created (Ollama not running or misconfigured)")
    return engine

def test_llamaindex_agent_basic(query_engine):
    # This will invoke the local Ollama Qwen3:1.7b model for synthesis
    response = query_engine.query("What is the transfer limit?")
    print("LLM Response:", response)
    assert "limit" in str(response).lower() or "$" in str(response)

def test_llamaindex_agent_graph_context():
    # Test that cypher utils work for a known clause type
    results = get_clauses_by_type("Limit")
    assert isinstance(results, list)
    if results:
        clause_id = results[0]["clause_id"]
        rels = get_related_clauses(clause_id, rel_type="REFERENCES", direction="out")
        assert isinstance(rels, list)
