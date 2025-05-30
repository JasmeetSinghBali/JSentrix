"""
infrastructure/load.py

Loads enriched clauses into Neo4j as vector nodes and creates relationships.
- Embeds clause text (using HuggingFace).
- Stores nodes and relationships in Neo4j (via LangChain and direct Cypher).
- Supports scoring, decay, and schema sync for downstream RAG/LLM use.

Usage:
    from infrastructure.load import load_to_neo4j

    load_to_neo4j(clauses)
"""

from langchain_neo4j import Neo4jVector
from langchain_core.documents import Document

from utils.embedding_utils import get_langchain_embedding_model
from utils.neo4j_utils import get_neo4j_config
from utils.logger import get_logger

from neo4j import GraphDatabase

import json
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = get_logger("jsentrix")


def clear_neo4j_database(config: Dict[str, Any]) -> None:
    """
    Removes all nodes and relationships from the Neo4j database.

    Args:
        config (Dict[str, Any]): Neo4j connection configuration.

    Returns:
        None
    """
    logger.info("Clearing all nodes and relationships in Neo4j database...")
    driver = GraphDatabase.driver(
        config["url"], auth=(config["username"], config["password"])
    )
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    driver.close()


def load_to_neo4j(clauses: List[Dict[str, Any]]) -> None:
    """
    Loads clauses into Neo4j as vector nodes and creates relationships.

    Args:
        clauses (List[Dict[str, Any]]): List of clause dicts (enriched).

    Returns:
        None
    """
    config = get_neo4j_config()
    clear_neo4j_database(config)
    embedding = get_langchain_embedding_model()

    # pre docs for vector ingestion(nodes)
    docs = []
    for cl in clauses:
        metadata = cl.get("metadata", {})
        # 🕊️ to support scoring and decay custom setup
        scoring_fields = {
            "score": 0.8,  # default to 0.8 for room of reward and penalty
            "last_accessed_at": datetime.now(
                timezone.utc
            ).isoformat(),  # for future decay
        }
        # 📌 llamaIndex required fields node_content and node_type schema sync during ingestion
        metadata = {
            **metadata,  # copy existing
            **scoring_fields,
            "_node_content": json.dumps(
                {"text": cl["text"]}
            ),  # llamaindex expects this as json string represent
            "_node_type": "TextNode",
        }
        docs.append(Document(page_content=cl["text"], metadata=metadata))
    if docs:
        logger.info(f"Injecting doc to neo4j: \n{docs}")

    Neo4jVector.from_documents(
        docs,
        embedding=embedding,
        url=config["url"],
        username=config["username"],
        password=config["password"],
        index_name=config["index_name"],
        node_label=config["node_label"],
        embedding_node_property=config["embedding_property"],
        pre_delete_collection=True,  # clear's previous data
    )

    # create relationship via neo4j driver
    driver = GraphDatabase.driver(
        config["url"], auth=(config["username"], config["password"])
    )

    with driver.session() as session:
        # create unique constraint on clause_id for effective matching
        session.run(
            """
            CREATE CONSTRAINT IF NOT EXISTS FOR (c:ComplianceClause)
            REQUIRE c.clause_id IS UNIQUE
        """
        )

        for cl in clauses:
            src_id = cl["id"]
            if not src_id:
                continue

            # helper func to create relationships of given type
            def create_relationship(rel_type: str, targets: List[str]) -> None:
                for tgt_id in targets:
                    tgt_id = tgt_id.strip()
                    if tgt_id:
                        logger.debug(f"Creating {rel_type} from {src_id} to {tgt_id}")
                        session.run(
                            f"""
                            MATCH (a:ComplianceClause {{clause_id:$src_id}}), (b:ComplianceClause {{clause_id: $tgt_id}})
                            MERGE (a)-[:{rel_type}]->(b)
                            """,
                            src_id=src_id,
                            tgt_id=tgt_id,
                        )

            metadata = cl.get("metadata", {})
            create_relationship("REFERENCES", metadata.get("references", []))
            create_relationship("AMENDS", metadata.get("amends", []))
            create_relationship("OVERRIDES", metadata.get("overrides", []))
    driver.close()
    logger.info(f"Injested {len(clauses)} clauses with ndes and relationshp into neo4j")
