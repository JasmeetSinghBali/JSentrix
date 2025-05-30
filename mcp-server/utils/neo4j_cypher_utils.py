"""
    Neo4j cyphe query utils reusable functions

    Usage:
        from utils.neo4j_cypher_utils import (
            get_clauses_by_type,
            get_clause_details,
            get_related_clauses,
            traverse_multi_hop,
        )

        # Example: Get all "Prohibition" type clauses
        prohibitions = get_clauses_by_type("Prohibition")
        print(prohibitions)

        # Example: Get all properties of clause C10
        details = get_clause_details("C10")
        print(details)

        # Find all clauses C4 REFERENCES
        forward = get_related_clauses("C4", rel_type="REFERENCES", direction="out")
        print("C4 references:", forward)

        # Find all clauses that reference C4 (reverse)
        backward = get_related_clauses("C4", rel_type="REFERENCES", direction="in")
        print("Clauses referencing C4:", backward)

        # Multi-hop traversal: find all clauses reachable from C4 via REFERENCES in 2 hops
        multi = traverse_multi_hop("C4", rel_type="REFERENCES", hops=2)
        print("Multi-hop REFERENCES from C4:", multi)

        # After retrieving a clause it can be traversed for its graph context:
        for doc in results:
            clause_id = doc.metadata.get("clause_id")
            print(f"Clause {clause_id} REFERENCES:", get_related_clauses(clause_id, "REFERENCES", "out"))
            print(f"Referenced BY:", get_related_clauses(clause_id, "REFERENCES", "in"))
            print(f"OVERRIDES:", get_related_clauses(clause_id, "OVERRIDES", "out"))
            print(f"AMENDS:", get_related_clauses(clause_id, "AMENDS", "out"))


"""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from neo4j.exceptions import Neo4jError

from .neo4j_utils import get_neo4j_driver
from .logger import get_logger

logger = get_logger("jsentrix")


def run_cypher_query(
    query: str, parameters: Optional[Dict[str, Any]] = None
) -> List[Dict[str, Any]]:
    """
    Runs an arbitrary Cypher query and returns a list of dict results.
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


def get_clauses_by_type(clause_type: str) -> List[Dict[str, Any]]:
    """
    Returns all clauses semantic filter of a given clause_type.
    """
    query = """
    MATCH (c:ComplianceClause {clause_type: $clause_type})
    RETURN c.clause_id AS clause_id, c.title AS title, c.text AS text
    """
    return run_cypher_query(query, {"clause_type": clause_type})


def get_clause_details(clause_id: str) -> List[Dict[str, Any]]:
    """
    Returns all node properties for a given clause_id.
    """
    query = """
    MATCH (c:ComplianceClause {clause_id: $clause_id})
    RETURN c
    """
    return run_cypher_query(query, {"clause_id": clause_id})


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
