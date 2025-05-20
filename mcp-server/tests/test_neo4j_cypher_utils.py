import pytest
from utils.neo4j_cypher_utils import (
    get_clauses_by_type,
    get_clause_details,
    get_related_clauses,
    traverse_multi_hop,
    run_cypher_query,
)

@pytest.mark.parametrize("clause_type", ["Limit", "Prohibition", "Rule"])
def test_get_clauses_by_type(clause_type):
    results = get_clauses_by_type(clause_type)
    assert isinstance(results, list)
    # If you have at least one clause of this type, this will pass
    if results:
        for r in results:
            assert r["clause_id"]
            assert r["title"]

def test_get_clause_details():
    details = get_clause_details("C4")
    assert isinstance(details, list)
    if details:
        c = details[0]
        assert "c" in c
        assert c["c"]["clause_id"] == "C4"

def test_get_related_clauses_forward_and_reverse():
    # Forward traversal (e.g., C4 REFERENCES others)
    forward = get_related_clauses("C4", rel_type="REFERENCES", direction="out")
    assert isinstance(forward, list)
    # Reverse traversal (e.g., who REFERENCES C4)
    reverse = get_related_clauses("C4", rel_type="REFERENCES", direction="in")
    assert isinstance(reverse, list)

def test_traverse_multi_hop():
    # 2-hop traversal from C4 via REFERENCES
    multi = traverse_multi_hop("C4", rel_type="REFERENCES", hops=2)
    assert isinstance(multi, list)
    if multi:
        for path in multi:
            assert "clause_path" in path
            assert isinstance(path["clause_path"], list)

def test_run_cypher_query():
    # Basic query to check database is reachable
    result = run_cypher_query("MATCH (n:ComplianceClause) RETURN count(n) AS count")
    assert isinstance(result, list)
    assert "count" in result[0]
