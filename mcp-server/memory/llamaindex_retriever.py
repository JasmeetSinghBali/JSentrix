from llama_index.vector_stores.neo4jvector import Neo4jVectorStore
from llama_index.core import VectorStoreIndex
from utils.neo4j_utils import get_neo4j_config
from utils.logger import get_logger

logger=get_logger(__name__)

def get_llamaindex_query_engine():
    """
    Returns:
        indexInstance: a LlamaIndex query engine instance/object connected to neo4j vector store
    """
    config = get_neo4j_config()
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
        index = VectorStoreIndex.from_vector_store(neo4j_vector)
        return index.as_query_engine()
    except Exception as e:
        logger.error(f"ERROR: {str(e)}")