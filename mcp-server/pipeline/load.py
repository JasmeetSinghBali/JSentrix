from langchain_neo4j import Neo4jVector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from utils.neo4j_utils import get_neo4j_config
from utils.logger import default_logger

def load_to_neo4j(clauses):
    config = get_neo4j_config()
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")  # 384d, CPU-friendly
    docs = [
        Document(page_content=cl["text"], metadata=cl["metadata"])
        for cl in clauses
    ]
    if docs:
        default_logger.info(f"Injecting doc to neo4j: \n{docs}")
    Neo4jVector.from_documents(
        docs,
        embedding=embedding,
        url=config["url"],
        username=config["username"],
        password=config["password"],
        index_name=config["index_name"],
        node_label=config["node_label"],
        embedding_node_property=config["embedding_property"]
    )
