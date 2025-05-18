import pytest
from memory.langchain_retriever import GraphMemoryRetriever

class MockLangChainAgent:
    def __init__(self, memory):
        self.memory = memory

    def run(self, query):
        results = self.memory.get_relevant(query)
        return [doc.page_content for doc in results]

@pytest.fixture
def memory():
    return GraphMemoryRetriever()

def test_langchain_agent(memory):
    # Add mock memory
    memory.add_memory("The transfer limit is $10,000 per month.", {"clause_type": "Limit"})
    agent = MockLangChainAgent(memory=memory)
    results = agent.run("What is the transfer limit?")
    assert any("10,000" in r for r in results)
