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

from neo4j import GraphDatabase
from .neo4j_utils import get_neo4j_config

def run_cypher_query(query, parameters=None):
    """
    Runs an arbitrary Cypher query and returns a list of dict results.
    """
    config = get_neo4j_config()
    driver = GraphDatabase.driver(config["url"], auth=(config["username"], config["password"]))
    with driver.session() as session:
        result = session.run(query, parameters or {})
        data = [record.data() for record in result]
    driver.close()
    return data

def get_clauses_by_type(clause_type):
    """
    Returns all clauses semantic filter of a given clause_type.
    """
    query = """
    MATCH (c:ComplianceClause {clause_type: $clause_type})
    RETURN c.clause_id AS clause_id, c.title AS title, c.text AS text
    """
    return run_cypher_query(query, {"clause_type": clause_type})

def get_clause_details(clause_id):
    """
    Returns all node properties for a given clause_id.
    """
    query = """
    MATCH (c:ComplianceClause {clause_id: $clause_id})
    RETURN c
    """
    return run_cypher_query(query, {"clause_id": clause_id})

def get_related_clauses(clause_id, rel_type="REFERENCES", direction="out"):
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

def traverse_multi_hop(clause_id, rel_type="REFERENCES", hops=2):
    """
    Traverse multiple hops of a given relationship type from a clause.
    """
    query = f"""
        MATCH (start:ComplianceClause {{clause_id: $clause_id}})
        MATCH path = (start)-[:{rel_type}*1..{hops}]->(end:ComplianceClause)
        RETURN [n IN nodes(path) | n.clause_id] AS clause_path
    """
    return run_cypher_query(query, {"clause_id": clause_id})