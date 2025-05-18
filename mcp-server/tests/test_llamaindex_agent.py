import pytest
from memory.llamaindex_retriever import get_llamaindex_query_engine

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

def test_llamaindex_agent(query_engine):
    # This will invoke the local Ollama Qwen3:1.7b model for synthesis
    response = query_engine.query("What is the transfer limit?")
    print("LLM Response:", response)
    assert "limit" in str(response).lower() or "$" in str(response)
