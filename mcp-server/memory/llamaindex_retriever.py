from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.neo4jvector import Neo4jVectorStore
from llama_index.core import VectorStoreIndex
from llama_index.core.retrievers import VectorIndexRetriever
from llama_index.core.query_engine import RetrieverQueryEngine
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
    neo4j_vector=Neo4jVectorStore(
        username=config["username"],
        password=config["password"],
        url=config["url"],
        embedding_dimension=384, # must match with dim that used during knowledge base prep i.e inges+index pipeline
        index_name=config["index_name"],
        text_node_property=config["text_property"],
        node_label=config["node_label"],
        embedding_node_property=config["embedding_property"],
    )
    try:
        index = VectorStoreIndex.from_vector_store(neo4j_vector,embed_model=embed_model)
        retriever=VectorIndexRetriever(index=index,similarity_top_k=2)
        # 📌 No llm just retriever instance custom return
        query_engine=RetrieverQueryEngine(retriever=retriever)
        return query_engine
    except Exception as e:
        logger.error(f"ERROR: {str(e)}")
        return None