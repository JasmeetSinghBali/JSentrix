from llama_index.llms.ollama import Ollama
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.neo4jvector import Neo4jVectorStore
from llama_index.core import VectorStoreIndex
from utils.neo4j_utils import get_neo4j_config
from utils.logger import get_logger

logger=get_logger(__name__)

def get_llamaindex_query_engine():
    """
    Returns:
        queryEngineRetrieverOnly: a LlamaIndex query engine retriever only connected to neo4j vector store
    """
    config = get_neo4j_config()
    embed_model = HuggingFaceEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    # Ollama served Qwen3:1.7b model at localhost:11434 Ollama class connects to it
    llm=Ollama(model="qwen3:1.7b",request_timeout=120.0)
    neo4j_vector=Neo4jVectorStore(
        username=config["username"],
        password=config["password"],
        url=config["url"],
        embedding_dimension=384, # must match with dim that used during knowledge base prep i.e inges+index pipeline
        index_name=config["index_name"],
        text_node_property=config["text_property"],
        node_label=config["node_label"],
        embedding_node_property=config["embedding_property"],
        # 📌 Custom Cypher Query to explicitly map LangChain node properties (text, clause_type, etc.) to the metadata fields LlamaIndex expects (_node_content, _node_type)
        # preserves original metadata clause_type and source for filtering
        # 🎈 make sure this shud always sync with the schema during ingestion pipeline 
        # custom_query="""
        # MATCH (n: `ComplianceClause`)
        # RETURN
        #     n.text AS text,
        #     n.embedding AS embedding,
        #     {
        #         id: elementId(n),
        #         _node_content: n.text,
        #         _node_type: 'TextNode',
        #         clause_type: n.clause_type,
        #         source: n.source
        #     } AS metadata
        # """
    )
    try:
        index = VectorStoreIndex.from_vector_store(neo4j_vector,embed_model=embed_model)
        # 📌 local qwen3 local llm for synthesis
        return index.as_query_engine(llm=llm)
    except Exception as e:
        logger.error(f"ERROR: {str(e)}")
        return None