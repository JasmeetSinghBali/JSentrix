import os
from typing import Dict
from dotenv import load_dotenv
from utils.logger import get_logger

logger = get_logger("jsentrix")

load_dotenv()

DEFAULT_INDEX_NAME = "compliance_clauses"
DEFAULT_NODE_LABEL = "ComplianceClause"
DEFAULT_TEXT_PROPERTY = "text"
DEFAULT_EMBEDDING_PROPERTY = "embedding"

_neo4j_config = None

def get_env_var(key: str, default: str = None, required: bool = False) -> str:
    value = os.getenv(key, default)
    if required and not value:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return value

def get_neo4j_config() -> Dict[str, str]:
    global _neo4j_config
    if _neo4j_config is None:
        logger.debug("Initializing Neo4j config...")
        _neo4j_config= {
            "url": get_env_var("NEO4J_URI", required=True),
            "username": get_env_var("NEO4J_USERNAME", required=True),
            "password": get_env_var("NEO4J_PASSWORD", required=True),
            "index_name": get_env_var("NEO4J_INDEX_NAME", DEFAULT_INDEX_NAME),
            "node_label": get_env_var("NEO4J_NODE_LABEL", DEFAULT_NODE_LABEL),
            "text_property": get_env_var("NEO4J_TEXT_PROPERTY", DEFAULT_TEXT_PROPERTY),
            "embedding_property": get_env_var("NEO4J_EMBEDDING_PROPERTY", DEFAULT_EMBEDDING_PROPERTY),
        }
    return _neo4j_config

# --- for driver pooling ---
from neo4j import GraphDatabase
_neo4j_driver = None

def get_neo4j_driver():
    global _neo4j_driver
    if _neo4j_driver is None:
        config = get_neo4j_config()
        logger.debug("Initializing Neo4j driver...")
        _neo4j_driver = GraphDatabase.driver(
            config["url"],
            auth=(config["username"], config["password"])
        )
    return _neo4j_driver
