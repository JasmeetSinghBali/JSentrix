from langchain_community.vectorstores import Neo4jVector
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
import os

def load_to_neo4j(clauses):
    model = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")  # 384d, CPU-friendly
    docs = [
        Document(page_content=cl["text"], metadata=cl["metadata"])
        for cl in clauses
    ]
    Neo4jVector.from_documents(
        docs,
        embedding=model,
        url=os.getenv("NEO4J_URI"),
        username=os.getenv("NEO4J_USERNAME"),
        password=os.getenv("NEO4J_PASSWORD"),
        index_name="compliance_clauses",
        node_label="ComplianceClause",
        embedding_node_property="embedding"
    )
