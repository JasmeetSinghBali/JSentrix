from typing import Dict, List, Any, Optional
from langchain_neo4j import Neo4jVector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from utils.neo4j_utils import get_neo4j_config
from utils.logger import get_logger
from utils.neo4j_cypher_utils import run_cypher_query

logger=get_logger(__name__)


class GraphMemoryRetriever:
    """
    Langchain compatible retriever using Neo4j vector store
    <update: 20may-2025> supports metadata filtering and inspection

    Usage:
        retriever = GraphMemoryRetriever()

        # Get all filterable fields
        print(retriever.get_filterable_fields())

        # Get all unique clause types
        print(retriever.get_unique_values_for_field("clause_type"))

        # Retrieve only "Prohibition" type clauses relevant to a query
        results = retriever.get_relevant(
            "cross-border payments",
            filter_metadata={"clause_type": "Prohibition"}
        )
        for doc in results:
            print(doc.metadata)
    """
    def __init__(
            self,
            embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
            top_k: int = 5
        ):
        config=get_neo4j_config()
        self.embedding=HuggingFaceEmbeddings(model_name=embedding_model_name)
        self.top_k = top_k

        self.vectorstore = Neo4jVector(
            embedding=self.embedding,
            url=config["url"],
            username=config["username"],
            password=config["password"],
            index_name=config["index_name"],
            node_label=config["node_label"],
            embedding_node_property=config["embedding_property"],
        )

    def get_relevant(
            self,
            query:str,
            top_k:Optional[int]=None,
            filter_metadata: Optional[Dict[str,Any]]=None)->List[Document]:
        """
        Get relevant top_k results from passed query with optional metadata filtering support

        Usage:
            filter_metadata = {"clause_type": "Prohibition"}
            filter_metadata = {"category": "NarrativeText", "source": "data/sample_compliance.md"}

        Args:
            query (str): query
            top_k (Optional[int], optional): number of matched top k results count. Defaults to None.
            filter_metadata (Optional[Dict[str,Any]], optional): additional metadata filter for query. Defaults to None.

        Returns:
            List[Document]: returns list of Document matching the query
        """
        top_k=top_k or self.top_k
        try:
            results=self.vectorstore.similarity_search(
            query,
            k=top_k,
            filter=filter_metadata)
            if results is None:
                return []
            return results
        except Exception as e:
            logger.error(f"ERROR: {str(e)}")
            return []
    
    def add_memory(self, text:str, metadata:Optional[Dict[str,Any]]=None):
        """
        Adds {text and metadata} as a new Document to the vector store memory

        Args:
            text (str): extracted text
            metadata (Optional[[str,Any]], optional): metadata for the extracted text. Defaults to None.
        """
        try:
            doc=Document(page_content=text,metadata=metadata or {})
            if doc:
                logger.debug(f"Adding new doc to Neo4j: {str(doc)}")
            self.vectorstore.add_documents([doc])
        except Exception as e:
            logger.error(f"ERROR: {str(e)}")

    def get_all(self)->List[Document]:
        try:
            return self.vectorstore.similarity_search("",k=1000)
        except Exception as e:
            logger.error(f"ERROR: {str(e)}")
    
    def get_filterable_fields(self)->List[str]:
        """
        Returns:
            List[str]: list of all filterable metadata fields
        """
        # 🎈 This should match the schema in neo4j and ingestion pipeline
        return [
            "clause_id", "title", "clause_type", "category", "section_header",
            "references", "amends", "overrides", "source", "num_sentences", "entities"
        ]
    def get_unique_values_for_field(self,field:str)->List[Any]:
        """
        Returns:
            List[Any]: List of all uniq values for given metadata field in neo4j
        """
        query=f"""
        MATCH (n:ComplianceClause)
        RETURN DISTINCT n.{field} AS value
        """
        results = run_cypher_query(query)
        return [r["value"] for r in results if r["value"] is not None]