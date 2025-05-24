import pytest
from neo4j import GraphDatabase
from utils.neo4j_utils import get_neo4j_config

def test_neo4j_compliance_clause_metadata():
    config = get_neo4j_config()
    driver = GraphDatabase.driver(config["url"], auth=(config["username"], config["password"]))
    with driver.session() as session:
        result = session.run("""
            MATCH (n:ComplianceClause)
            RETURN
                n.text AS text,
                n.embedding AS embedding,
                {
                    id: elementId(n),
                    clause_id: n.clause_id,
                    title: n.title,
                    clause_type: n.clause_type,
                    references: n.references,
                    amends: n.amends,
                    overrides: n.overrides,
                    source: n.source,
                    category: n.category,
                    section_header: n.section_header,
                    num_sentences: n.num_sentences,
                    entities: n.entities,
                    _node_content: n.text,
                    _node_type: 'TextNode'
                } AS metadata
            LIMIT 5
        """)
        found = False
        for record in result:
            metadata = record["metadata"]
            print("Neo4j node metadata:", metadata)
            # Assert that key fields are present and not None
            assert "clause_id" in metadata and metadata["clause_id"] is not None, "Missing clause_id"
            assert "title" in metadata and metadata["title"] is not None, "Missing title"
            found = True
        assert found, "No ComplianceClause nodes found in Neo4j!"
    driver.close()
