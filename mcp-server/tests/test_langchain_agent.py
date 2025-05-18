import pytest
import json
from memory.langchain_retriever import GraphMemoryRetriever

class MockLangChainAgent:
    """
    LangChain mock agent: Only retrieves, does not use an LLM for synthesis.
    """
    def __init__(self, memory):
        self.memory = memory

    def run(self, query):
        results = self.memory.get_relevant(query)
        return [doc.page_content for doc in results]

@pytest.fixture
def memory():
    return GraphMemoryRetriever()

def test_langchain_agent(memory):
    # Add mock memory with LlamaIndex-compatible metadata
    text = "The transfer limit is $10,000 per month."
    metadata = {
        "clause_type": "Limit",
        "_node_content": json.dumps({"text": text}),
        "_node_type": "TextNode"
    }
    memory.add_memory(text, metadata)
    agent = MockLangChainAgent(memory=memory)
    results = agent.run("What is the transfer limit?")
    assert any("10,000" in r for r in results)
