import pytest
from memory.llamaindex_retriever import get_llamaindex_query_engine

class MockLlamaIndexAgent:
    def __init__(self, query_engine):
        self.query_engine = query_engine

    def run(self, query):
        response = self.query_engine.query(query)
        return str(response)

@pytest.fixture
def query_engine():
    return get_llamaindex_query_engine()

def test_llamaindex_agent(query_engine):
    agent = MockLlamaIndexAgent(query_engine=query_engine)
    response = agent.run("What is the transfer limit?")
    assert "limit" in response.lower() or "$" in response
