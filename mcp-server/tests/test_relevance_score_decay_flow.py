import pytest
from datetime import datetime, timezone

from utils.relevance_scorer import RelevanceScorer
from utils.llamaindex_postprocessors import CustomRelevancePostprocessor

from memory.langchain_retriever import GraphMemoryRetriever
from memory.llamaindex_retriever import get_llamaindex_query_engine

from utils.neo4j_utils import get_neo4j_config
from utils.neo4j_cypher_utils import get_clause_details, update_clause_metadata

# --- Fixtures for real retrievers and query engines ---

@pytest.fixture
def memory():
    """Real GraphMemoryRetriever instance with Neo4j connection."""
    return GraphMemoryRetriever()

@pytest.fixture(scope="module")
def query_engine():
    """Real LlamaIndex query engine (skip if not available)."""
    engine = get_llamaindex_query_engine()
    if engine is None:
        pytest.skip("LlamaIndex query engine could not be created (Ollama not running or misconfigured)")
    return engine

@pytest.fixture
def scorer():
    """Relevance scorer instance for scoring and decay."""
    return RelevanceScorer(base_score=0.8, decay_rate=0.1)

@pytest.fixture
def postprocessor(scorer):
    """Postprocessor that applies decay scoring."""
    return CustomRelevancePostprocessor(scorer)

# --- Mock agents but real retrieval and scoring ---

class MockLangChainAgent:
    """
    Mock LangChain agent that orchestrates retrieval from GraphMemoryRetriever.
    Only calls real retrieval, does not synthesize answer.
    """
    def __init__(self, memory):
        self.memory = memory

    def run(self, query, filter_metadata=None):
        results = self.memory.get_relevant(query, filter_metadata=filter_metadata)
        return results

class MockLlamaIndexAgent:
    """
    Mock LlamaIndex agent: uses real query engine with LLM inference and postprocessing for scoring.
    - retrieve,

    - run the LLM to synthesize the final answer,

    - then extract the relevant nodes from the response,

    - do custom scoring/postprocessing,

    - reward/penalize,

    - update Neo4j metadata i.e updated score with dynamic decayed_score value and last_accessed_at
    """
    def __init__(self, query_engine, scorer, postprocessor):
        self.query_engine = query_engine
        self.scorer = scorer
        self.postprocessor = postprocessor

    def retrieve_and_rank(self, query):
        # Call the real query engine's query method, triggering LLM inference and retrieval
        response = self.query_engine.query(query)

        # response might be a string or an object depending on LlamaIndex version
        # If response has nodes, extract them; else fallback
        nodes = []
        if hasattr(response, "source_nodes"):
            nodes = response.source_nodes
        elif hasattr(response, "nodes"):
            nodes = response.nodes

        # Defensive fallback: If no nodes, return empty
        if not nodes:
            return []

        # Score nodes and apply postprocessing (decay, reranking)
        ranked_nodes = self.postprocessor.postprocess_nodes(nodes, query)
        return ranked_nodes

    def reward_node(self, node):
        self.scorer.reward(node.metadata)
        clause_id = node.metadata.get('clause_id')
        if clause_id:
            update_clause_metadata(clause_id, node.metadata)

    def penalize_node(self, node):
        self.scorer.penalize(node.metadata)
        clause_id = node.metadata.get('clause_id')
        if clause_id:
            update_clause_metadata(clause_id, node.metadata)



# --- Tests ---

def test_relevance_score_decay_flow(memory, query_engine, scorer, postprocessor):
    """
    End-to-end test:
    1) LangChain mock agent retrieves docs from real memory
    2) LlamaIndex mock agent calls real query engine for LLM inference, scoring, ranking
    3) Top scored doc rewarded, others penalized
    4) Metadata updated in Neo4j
    """

    # Initialize agents with real retriever and scoring
    langchain_agent = MockLangChainAgent(memory)
    llama_agent = MockLlamaIndexAgent(query_engine, scorer, postprocessor)

    query = "What is the transfer limit?"

    # Step 1: LangChain agent retrieves relevant docs (optional check)
    retrieved_docs = langchain_agent.run(query)
    assert len(retrieved_docs) > 0, "LangChain agent should retrieve some docs"

    # Step 2: LlamaIndex agent calls real query engine to run retrieval + LLM inference
    ranked_nodes = llama_agent.retrieve_and_rank(query)
    assert len(ranked_nodes) > 0, "LlamaIndex agent should rank nodes after LLM inference"

    # Step 3: Reward top node, penalize others
    top_node = ranked_nodes[0]
    pre_reward_score = top_node.metadata.get("score", 0.8)

    llama_agent.reward_node(top_node)
    for node in ranked_nodes[1:]:
        llama_agent.penalize_node(node)

    # Step 4: Verify metadata updates in Neo4j
    updated_top_meta = get_clause_details(top_node.metadata['clause_id'])[0]['c']
    updated_score = updated_top_meta['score']
    updated_last_accessed = updated_top_meta.get('last_accessed_at')

    assert updated_score > pre_reward_score, "Top node score should increase after reward"
    assert updated_last_accessed is not None, "Last accessed timestamp should be updated"

    for node in ranked_nodes[1:]:
        updated_meta = get_clause_details(node.metadata['clause_id'])[0]['c']
        assert updated_meta['score'] < node.metadata['score'], "Penalized nodes should have decreased score"

    print("End-to-end relevance score decay flow test passed.")
