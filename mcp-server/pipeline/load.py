from langchain_neo4j import Neo4jVector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from utils.neo4j_utils import get_neo4j_config
from utils.logger import default_logger
import json

def load_to_neo4j(clauses):
    config = get_neo4j_config()
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")  # 384d, CPU-friendly
    docs=[]
    for cl in clauses:
        text=cl["text"]
        metadata=cl.get("metadata",{})
        # 📌 llamaIndex required fields node_content and node_type schema sync during ingestion
        metadata={
            **metadata, # copy existing
            "_node_content": json.dumps({"text": text}), # llamaindex expects this as json string represent
            "_node_type": "TextNode"
        }
        docs.append(Document(page_content=text, metadata=metadata))
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
