from typing import Dict, List, Any, Optional
from langchain_neo4j import Neo4jVector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from utils.neo4j_utils import get_neo4j_config
from utils.logger import get_logger
from utils.neo4j_cypher_utils import run_cypher_query
import math
from datetime import datetime,timezone
from utils.neo4j_cypher_utils import update_last_accessed
from utils.relevance_scorer import RelevanceScorer

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
            top_k: int = 5,
            scorer: Optional[RelevanceScorer] = None
        ):
        config=get_neo4j_config()
        self.scorer = scorer or RelevanceScorer()
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
            filter_metadata: Optional[Dict[str,Any]]=None,
            apply_decay: bool = True,
            rescore: bool = False,
        )->List[Document]:
        """
        Get relevant top_k results from passed query with optional metadata filtering support, decay sorting and scoring

        Usage:
            retriever = GraphMemoryRetriever()
            results = retriever.get_relevant(
                query="Which clauses override data retention?",
                filter_metadata={"clause_type": "Override"},
                rescore=True  #  Use RelevanceScorer here
            )
            💫
            If you want to use the hybrid scoring (semantic × decay), you must call get_relevant(..., rescore=True).

            If you want only decay-based sorting, call with rescore=False (or omit it, since default is False) and leave apply_decay=True.

            If you want pure vectorstore ranking (no decay), call with apply_decay=False, rescore=False.

            Example:
                # Hybrid scoring (recommended for most use cases)
                results = retriever.get_relevant("query", rescore=True)

                # Only decay-based scoring
                results = retriever.get_relevant("query", apply_decay=True, rescore=False)

                # No decay, just vectorstore similarity
                results = retriever.get_relevant("query", apply_decay=False, rescore=False)

        Args:
            query (str): The search query.
            top_k (Optional[int]): Number of results to return. Defaults to self.top_k.
            filter_metadata (Optional[Dict[str, Any]]): Metadata filters (e.g., {"clause_type": "Prohibition"}).
            apply_decay (bool): Whether to apply time-based decay to sorting.
            rescore (bool): Whether to rescore using custom RelevanceScorer after retrieval.

        Returns:
            List[Document]: List of relevant documents.
        """
        top_k=top_k or self.top_k
        try:
            results=self.vectorstore.similarity_search(
                query,
                k=top_k,
                filter=filter_metadata
            )
            if results is None:
                return []
            # optional rescoring
            # custom_score 
            # By default, your Neo4jVector.similarity_search() ranks results based on vector similarity (cosine similarity, etc.). But vector similarity:
            # Does not consider freshness or recency.
            # Does not account for business-specific factors (like clause type priority, source, or user engagement).
            # May surface stale or less relevant content in certain compliance or evolving domains.
            # So:
            # custom_score lets you override or refine the default ranking by applying additional logic after the raw retrieval.
            # Let’s say these are retrieved based on cosine similarity:
            # Document	Cosine Score	Last Accessed	custom_score (decayed)
            # A	            0.94	        30 days ago	    0.75
            # B	            0.91	        1 day ago	    0.88
            # C	            0.89	        90 days ago	    0.50
            # If sort by custom_score, result B moves above A and C — prioritizing recency, not just vector proximity.
            # 📌 hybrid scoring = original_score/similarity score*decayed_score
            if rescore:
                for doc in results:
                    sim_score = doc.metadata.get("score",0.8)
                    decayed_score=self.scorer.score(doc.metadata)
                    hybrid_score=sim_score*decayed_score
                    doc.metadata["hybrid_score"] = hybrid_score
                    doc.metadata["sim_core"] = sim_score
                    doc.metadata["decayed_score"] = decayed_score
                    logger.debug(
                        f"Doc {doc.metadata.get('clause_id')}: sim_score={sim_score}, decayed_score={decayed_score}, hybrid_score={hybrid_score}"
                    )
                # 📌 finally sort by hybrid score
                results=sorted(results,key=lambda d: d.metadata.get("hybrid_score", 0),reverse=True)
            elif apply_decay:
                # only apply decay based sorting
                results=self._decay_aware_sort(results,apply_decay=True)
            
            # 📌 NOTE: Do NOT persist `score` to Neo4j — it's a transient value based on current time and decays over time.
            # update last accessed at for each document (if clause_id is available) as this document is just used/retrieved
            for doc in results:
                clause_id=doc.metadata.get("clause_id")
                if clause_id:
                    try:
                        update_last_accessed(clause_id)
                    except Exception as e:
                        logger.debug(f"failed to update last_accessed_at for {clause_id}: {str(e)}")
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
    
    def _apply_time_decay(self,score: float,last_accessed_at: str,decay_rate: float = 0.01)-> float:
        """
        Exponential decay to reduce score based on days since last accessed
        
        example
        If a document was last accessed long ago, it gets a lower score.
        decay_rate = 0.01 → after ~70 days, score drops to half.
        """
        try:
            last_dt = datetime.fromisoformat(last_accessed_at)
            days=(datetime.now(timezone.utc) - last_dt).days
            return score*math.exp(-decay_rate*days)
        except Exception as e:
            logger.error(str(e))
            return score # fallback if timestamp missing or invalid
    
    def _decay_aware_sort(self,docs: List[Document],apply_decay: bool=True)->List[Document]:
        """
        Sorts documents by decayed score based on last_accessed_at metadata
        """
        if not apply_decay:
            return docs
        try:
            return sorted(
                docs,
                key=lambda d: self.scorer.score(d.metadata),
                reverse=True
            )
        except Exception as e:
            logger.debug(f"fallback to default order due to scoring error: {str(e)}")
            return docs