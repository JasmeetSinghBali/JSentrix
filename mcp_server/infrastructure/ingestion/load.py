"""
infrastructure/ingestion/load.py

Loads enriched clauses into Neo4j as vector nodes and creates relationships.
- Embeds clause text (using HuggingFace).
- Stores nodes and relationships in Neo4j (via LangChain and direct Cypher).
- Supports scoring, decay, and schema sync for downstream RAG/LLM use.

Usage:
    from infrastructure.load import load_to_neo4j, async_load_to_neo4j

    load_to_neo4j(clauses)
    # or for async:
    await async_load_to_neo4j(clauses)
"""

from langchain_neo4j import Neo4jVector
from langchain_core.documents import Document

from utils.embedding_utils import (
    get_langchain_embedding_model,
    async_batch_embed_documents,
)
from utils.neo4j_utils import get_neo4j_config, get_async_neo4j_driver
from utils.logger import get_logger

from neo4j import GraphDatabase

import json
from datetime import datetime, timezone
from typing import List, Dict, Any

logger = get_logger("jsentrix")


def ensure_vector_index(driver, config, dimensions=384):
    index_name = config["index_name"]
    label = config["node_label"]
    property = config["embedding_property"]
    cypher_check = f"SHOW INDEXES WHERE name = '{index_name}'"
    cypher_create = f"""
    CREATE VECTOR INDEX {index_name}
    FOR (n:{label}) ON (n.{property})
    OPTIONS {{
      indexConfig: {{
        `vector.dimensions`: {dimensions},
        `vector.similarity_function`: 'cosine'
      }}
    }}
    """
    with driver.session() as session:
        result = session.run(cypher_check)
        indexes = list(result)
        if not indexes:
            logger.info(f"Creating vector index: {index_name}")
            session.run(cypher_create)
        else:
            logger.info(f"Vector index '{index_name}' already exists.")


async def ensure_vector_index_async(driver, config, dimensions=384):
    index_name = config["index_name"]
    label = config["node_label"]
    property = config["embedding_property"]
    cypher_check = f"SHOW INDEXES WHERE name = '{index_name}'"
    cypher_create = f"""
    CREATE VECTOR INDEX {index_name}
    FOR (n:{label}) ON (n.{property})
    OPTIONS {{
      indexConfig: {{
        `vector.dimensions`: {dimensions},
        `vector.similarity_function`: 'cosine'
      }}
    }}
    """
    async with driver.session() as session:
        result = await session.run(cypher_check)
        indexes = await result.values()
        if not indexes:
            logger.info(f"Creating vector index: {index_name}")
            await session.run(cypher_create)
        else:
            logger.info(f"Vector index '{index_name}' already exists.")


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
    driver = GraphDatabase.driver(
        config["url"], auth=(config["username"], config["password"])
    )
    ensure_vector_index(driver, config, dimensions=384)

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


# --- ASYNC VERSION ---

import asyncio


async def async_clear_neo4j_database(config: Dict[str, Any]) -> None:
    """
    Async version: Removes all nodes and relationships from the Neo4j database.
    """
    logger.info("Clearing all nodes and relationships in Neo4j database (async)...")
    driver = get_async_neo4j_driver()
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")


async def async_load_to_neo4j(clauses: List[Dict[str, Any]]) -> None:
    """
    Async version: Loads clauses into Neo4j as vector nodes and creates relationships.

    Args:
        clauses (List[Dict[str, Any]]): List of clause dicts (enriched).

    Returns:
        None
    """
    config = get_neo4j_config()
    await async_clear_neo4j_database(config)
    driver = get_async_neo4j_driver()
    await ensure_vector_index_async(driver, config, dimensions=384)

    # Prepare docs for vector ingestion (nodes)
    docs = []
    texts = []
    for cl in clauses:
        metadata = cl.get("metadata", {})
        scoring_fields = {
            "score": 0.8,
            "last_accessed_at": datetime.now(timezone.utc).isoformat(),
        }
        metadata = {
            **metadata,
            **scoring_fields,
            "_node_content": json.dumps({"text": cl["text"]}),
            "_node_type": "TextNode",
        }
        docs.append(Document(page_content=cl["text"], metadata=metadata))
        texts.append(cl["text"])

    if docs:
        logger.info(f"Injecting doc to neo4j (async): \n{docs}")

    # Async embedding
    embeddings = await async_batch_embed_documents(texts, backend="langchain")

    # Insert nodes with embeddings
    async with driver.session() as session:
        # Create unique constraint on clause_id
        await session.run(
            """
            CREATE CONSTRAINT IF NOT EXISTS FOR (c:ComplianceClause)
            REQUIRE c.clause_id IS UNIQUE
            """
        )

        # Insert nodes
        for doc, embedding in zip(docs, embeddings):
            await session.run(
                f"""
                CREATE (c:{config["node_label"]} {{
                    clause_id: $clause_id,
                    text: $text,
                    embedding: $embedding,
                    metadata: $metadata
                }})
                """,
                clause_id=doc.metadata.get("clause_id") or doc.metadata.get("id"),
                text=doc.page_content,
                embedding=embedding,
                metadata=json.dumps(doc.metadata),
            )

        # Create relationships
        for cl in clauses:
            src_id = cl["id"]
            if not src_id:
                continue

            async def create_relationship(rel_type: str, targets: List[str]):
                for tgt_id in targets:
                    tgt_id = tgt_id.strip()
                    if tgt_id:
                        logger.debug(
                            f"Creating {rel_type} from {src_id} to {tgt_id} (async)"
                        )
                        await session.run(
                            f"""
                            MATCH (a:ComplianceClause {{clause_id:$src_id}}), (b:ComplianceClause {{clause_id: $tgt_id}})
                            MERGE (a)-[:{rel_type}]->(b)
                            """,
                            src_id=src_id,
                            tgt_id=tgt_id,
                        )

            metadata = cl.get("metadata", {})
            await create_relationship("REFERENCES", metadata.get("references", []))
            await create_relationship("AMENDS", metadata.get("amends", []))
            await create_relationship("OVERRIDES", metadata.get("overrides", []))

    logger.info(
        f"Ingested {len(clauses)} clauses with nodes and relationships into Neo4j (async)"
    )
