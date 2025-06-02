"""
utils/neo4j_cypher_utils.py

Neo4j Cypher query utilities for compliance clause graph operations.

Usage:
    from utils.neo4j_cypher_utils import (
        get_clauses_by_type,
        get_clause_details,
        get_related_clauses,
        traverse_multi_hop,
        async_run_cypher_query,
        # ...etc.
    )
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import asyncio

from neo4j.exceptions import Neo4jError

from .neo4j_utils import get_neo4j_driver, get_async_neo4j_driver
from .logger import get_logger

logger = get_logger("jsentrix")


def run_cypher_query(
    query: str, parameters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Runs an arbitrary Cypher query (sync) and returns a list of dict results.
    """
    driver = get_neo4j_driver()
    try:
        with driver.session() as session:
            result = session.run(query, parameters or {})
            data = [record.data() for record in result]
        logger.debug(f"Ran Cypher query: {query.strip()} with params: {parameters}")
        return data
    except Neo4jError as e:
        logger.error(f"Cypher query failed: {e}")
        return []


async def async_run_cypher_query(
    query: str, parameters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Runs an arbitrary Cypher query (async) and returns a list of dict results.
    """
    driver = get_async_neo4j_driver()
    try:
        async with driver.session() as session:
            result = await session.run(query, parameters or {})
            data = [record.data() async for record in result]
        logger.debug(
            f"Ran async Cypher query: {query.strip()} with params: {parameters}"
        )
        return data
    except Neo4jError as e:
        logger.error(f"Async Cypher query failed: {e}")
        return []


def get_clauses_by_type(clause_type: str) -> List[Dict[str, Any]]:
    """
    Returns all clauses of a given clause_type.
    """
    query = """
    MATCH (c:ComplianceClause {clause_type: $clause_type})
    RETURN c.clause_id AS clause_id, c.title AS title, c.text AS text
    """
    return run_cypher_query(query, {"clause_type": clause_type})


async def async_get_clauses_by_type(clause_type: str) -> List[Dict[str, Any]]:
    query = """
    MATCH (c:ComplianceClause {clause_type: $clause_type})
    RETURN c.clause_id AS clause_id, c.title AS title, c.text AS text
    """
    return await async_run_cypher_query(query, {"clause_type": clause_type})


def get_clause_details(clause_id: str) -> List[Dict[str, Any]]:
    """
    Returns all node properties for a given clause_id.
    """
    query = """
    MATCH (c:ComplianceClause {clause_id: $clause_id})
    RETURN c
    """
    return run_cypher_query(query, {"clause_id": clause_id})


async def async_get_clause_details(clause_id: str) -> List[Dict[str, Any]]:
    query = """
    MATCH (c:ComplianceClause {clause_id: $clause_id})
    RETURN c
    """
    return await async_run_cypher_query(query, {"clause_id": clause_id})


def get_related_clauses(
    clause_id: str, rel_type: str = "REFERENCES", direction: str = "out"
) -> List[Dict[str, Any]]:
    """
    Traverse relationships from a clause.
    direction: "out" (default) for outgoing, "in" for incoming.
    rel_type: "REFERENCES", "AMENDS", "OVERRIDES"
    """
    if direction == "out":
        query = f"""
            MATCH (a:ComplianceClause {{clause_id: $clause_id}})-[r:{rel_type}]->(b:ComplianceClause)
            RETURN b.clause_id AS related_clause_id, b.title AS related_title, type(r) AS rel_type
        """
    else:
        query = f"""
            MATCH (a:ComplianceClause)<-[r:{rel_type}]-(b:ComplianceClause {{clause_id: $clause_id}})
            RETURN a.clause_id AS related_clause_id, a.title AS related_title, type(r) AS rel_type
        """
    return run_cypher_query(query, {"clause_id": clause_id})


async def async_get_related_clauses(
    clause_id: str, rel_type: str = "REFERENCES", direction: str = "out"
) -> List[Dict[str, Any]]:
    if direction == "out":
        query = f"""
            MATCH (a:ComplianceClause {{clause_id: $clause_id}})-[r:{rel_type}]->(b:ComplianceClause)
            RETURN b.clause_id AS related_clause_id, b.title AS related_title, type(r) AS rel_type
        """
    else:
        query = f"""
            MATCH (a:ComplianceClause)<-[r:{rel_type}]-(b:ComplianceClause {{clause_id: $clause_id}})
            RETURN a.clause_id AS related_clause_id, a.title AS related_title, type(r) AS rel_type
        """
    return await async_run_cypher_query(query, {"clause_id": clause_id})


def traverse_multi_hop(
    clause_id: str, rel_type: str = "REFERENCES", hops: int = 2
) -> List[Dict[str, Any]]:
    """
    Traverse multiple hops of a given relationship type from a clause.
    """
    query = f"""
        MATCH (start:ComplianceClause {{clause_id: $clause_id}})
        MATCH path = (start)-[:{rel_type}*1..{hops}]->(end:ComplianceClause)
        RETURN [n IN nodes(path) | n.clause_id] AS clause_path
    """
    return run_cypher_query(query, {"clause_id": clause_id})


async def async_traverse_multi_hop(
    clause_id: str, rel_type: str = "REFERENCES", hops: int = 2
) -> List[Dict[str, Any]]:
    query = f"""
        MATCH (start:ComplianceClause {{clause_id: $clause_id}})
        MATCH path = (start)-[:{rel_type}*1..{hops}]->(end:ComplianceClause)
        RETURN [n IN nodes(path) | n.clause_id] AS clause_path
    """
    return await async_run_cypher_query(query, {"clause_id": clause_id})


def update_last_accessed(clause_id: str) -> None:
    """
    Updates the last_accessed_at timestamp for the clause with given clause_id.
    """
    driver = get_neo4j_driver()
    query = """
    MATCH (n:ComplianceClause {clause_id: $clause_id})
    SET n.last_accessed_at = $timestamp
    """
    try:
        with driver.session() as session:
            session.run(
                query,
                clause_id=clause_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        logger.debug(f"Updated last_accessed_at for clause {clause_id}")
    except Neo4jError as e:
        logger.error(f"Failed to update last_accessed_at for {clause_id}: {e}")


async def async_update_last_accessed(clause_id: str) -> None:
    driver = get_async_neo4j_driver()
    query = """
    MATCH (n:ComplianceClause {clause_id: $clause_id})
    SET n.last_accessed_at = $timestamp
    """
    try:
        async with driver.session() as session:
            await session.run(
                query,
                clause_id=clause_id,
                timestamp=datetime.now(timezone.utc).isoformat(),
            )
        logger.debug(f"Async updated last_accessed_at for clause {clause_id}")
    except Neo4jError as e:
        logger.error(f"Async failed to update last_accessed_at for {clause_id}: {e}")


def update_clause_metadata(clause_id: str, metadata: Dict[str, Any]) -> None:
    """
    Updates metadata properties on a ComplianceClause node by clause_id.
    Accepts a dict of property keys and values to update.
    """
    driver = get_neo4j_driver()
    set_clauses = ", ".join([f"n.{key} = ${key}" for key in metadata.keys()])
    params = {"clause_id": clause_id, **metadata}
    query = f"""
    MATCH (n:ComplianceClause {{clause_id: $clause_id}})
    SET {set_clauses}
    """
    try:
        with driver.session() as session:
            session.run(query, params)
        logger.debug(f"Updated metadata for clause {clause_id}: {metadata}")
    except Neo4jError as e:
        logger.error(f"Failed to update metadata for {clause_id}: {e}")


async def async_update_clause_metadata(
    clause_id: str, metadata: Dict[str, Any]
) -> None:
    driver = get_async_neo4j_driver()
    set_clauses = ", ".join([f"n.{key} = ${key}" for key in metadata.keys()])
    params = {"clause_id": clause_id, **metadata}
    query = f"""
    MATCH (n:ComplianceClause {{clause_id: $clause_id}})
    SET {set_clauses}
    """
    try:
        async with driver.session() as session:
            await session.run(query, params)
        logger.debug(f"Async updated metadata for clause {clause_id}: {metadata}")
    except Neo4jError as e:
        logger.error(f"Async failed to update metadata for {clause_id}: {e}")
