from typing import Dict, List, Any, Optional
from langchain_community.vectorstores import Neo4jVector
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from utils.neo4j_utils import get_neo4j_config
from utils.logger import get_logger

logger=get_logger(__name__)


class GraphMemoryRetriever:
    """
    Langchain compatible retriever using Neo4j vector store
    """
    def __int__(
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

    def get_Relevant(
            self,
            query:str,
            top_k:Optional[int]=None,
            filter_metadata: Optional[Dict[str,Any]]=None)->List[Document]:
        """
        Get relevant top_k results from passed query

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
            if isinstance(results,List[Any]):
                logger.debug(f"Results from Neo4j: {results}")
            return results
        except Exception as e:
            logger.error(f"ERROR: {str(e)}")
    
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
