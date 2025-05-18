class GraphMemoryRetriever:
    """
    Custom retriever interface for langchain agents,
    knitted with neo4j vector store with custom schema
    """

    def __int__(
            self,
            embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
            neo4j_url: Optional[str] = None,
            neo4j_username: Optional[str] = None,
            neo4j_password: Optional[str] = None,
            index_name: str = "compliance_clauses",
            node_label: str = "ComplianceClause",
            embedding_node_property: str = "embedding",
            top_k: int = 5
        ):
        self.embedding=HuggingFaceEmbeedings(model_name=embedding_model_name)
        self.neo4j_url = neo4j_url or os.getenv("NEO4J_URI")
        self.neo4j_username = neo4j_username or os.getenv("NEO4J_USERNAME")
        self.neo4j_password = neo4j_password or os.getenv("NEO4J_PASSWORD")
        self.index_name = index_name
        self.node_label = node_label
        self.embedding_node_property = embedding_node_property
        self.top_k = top_k

        self.vectorstore = Neo4jVector(
            embedding=self.embedding,
            url=self.neo4j_url,
            username=self.neo4j_username,
            password=self.neo4j_password,
            index_name=self.index_name,
            node_label=self.node_label,
            embedding_node_property=self.embedding_node_property,
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
        results=self.vectorstore.similarity_search(
            query,
            k=top_k,
            filter=filter_metadata)
        return results
    
    def add_memory(self,text:str,metadata:Optional[[str,Any]]=None):
        """
        Adds {text and metadata} as a new Document to the vector store memory

        Args:
            text (str): extracted text
            metadata (Optional[[str,Any]], optional): metadata for the extracted text. Defaults to None.
        """
        doc=Document(page_content=text,metadata=metadata or {})
        self.vectorstore.add_documents([doc])

    def get_all(self)->List[Document]:
        return self.vectorstore.similarity_search("",k=1000)
