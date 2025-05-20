from langchain_neo4j import Neo4jVector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from utils.neo4j_utils import get_neo4j_config
from utils.logger import default_logger
from neo4j import GraphDatabase
import json

def clear_neo4j_database(config):
    default_logger.info("Clearing all nodes and relationships in Neo4j database...")
    driver = GraphDatabase.driver(config["url"], auth=(config["username"], config["password"]))
    with driver.session() as session:
        session.run("MATCH (n) DETACH DELETE n")
    driver.close()


def load_to_neo4j(clauses):
    config = get_neo4j_config()
    clear_neo4j_database(config)
    embedding = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")  # 384d, CPU-friendly
    
    # pre docs for vector ingestion(nodes)
    docs=[]
    for cl in clauses:
        metadata=cl.get("metadata",{})
        # 📌 llamaIndex required fields node_content and node_type schema sync during ingestion
        metadata={
            **metadata, # copy existing
            "_node_content": json.dumps({"text": cl["text"]}), # llamaindex expects this as json string represent
            "_node_type": "TextNode"
        }
        docs.append(Document(page_content=cl["text"], metadata=metadata))
    if docs:
        default_logger.info(f"Injecting doc to neo4j: \n{docs}")
    Neo4jVector.from_documents(
        docs,
        embedding=embedding,
        url=config["url"],
        username=config["username"],
        password=config["password"],
        index_name=config["index_name"],
        node_label=config["node_label"],
        embedding_node_property=config["embedding_property"],
        pre_delete_collection=True # clear's previous data
    )

    # create relationship via neo4j driver
    driver = GraphDatabase.driver(
        config["url"],
        auth=(
            config["username"],
            config["password"]
        )
    )

    with driver.session() as session:
        # create unique constraint on clause_id for effective matching
        session.run("""
            CREATE CONSTRAINT IF NOT EXISTS FOR (c:ComplianceClause)
            REQUIRE c.clause_id IS UNIQUE
        """)

        for cl in clauses:
            src_id=cl["id"]
            if not src_id:
                continue
            
            # helper func to create relationships of given type
            def create_relationship(rel_type,targets):
                for tgt_id in targets:
                    tgt_id=tgt_id.strip()
                    if tgt_id:
                        default_logger.debug(f"Creating {rel_type} from {src_id} to {tgt_id}")
                        session.run(
                            f"""
                            MATCH (a:ComplianceClause {{clause_id:$src_id}}), (b:ComplianceClause {{clause_id: $tgt_id}})
                            MERGE (a)-[:{rel_type}]->(b)
                            """,
                            src_id=src_id,
                            tgt_id=tgt_id
                        )
            
            metadata = cl.get("metadata",{})
            create_relationship("REFERENCES",metadata.get("references",[]))
            create_relationship("AMENDS",metadata.get("amends",[]))
            create_relationship("OVERRIDES",metadata.get("overrides",[]))
    driver.close()
    default_logger.info(f"Injested {len(clauses)} clauses with ndes and relationshp into neo4j")
