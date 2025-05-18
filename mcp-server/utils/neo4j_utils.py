import os
from typing import Dict
from dotenv import load_dotenv
from utils.logger import default_logger

load_dotenv()

DEFAULT_INDEX_NAME = "compliance_clauses"
DEFAULT_NODE_LABEL = "ComplianceClause"
DEFAULT_TEXT_PROPERTY = "text"
DEFAULT_EMBEDDING_PROPERTY = "embedding"

def get_env_var(key: str, default: str = None, required: bool = False) -> str:
    """
    fetches environment variable with optional fallback and required enforcement.

    Args:
        key (str): Environment variable name
        default (str, optional): Fallback value if not found
        required (bool, optional): If True, raises error when missing

    Returns:
        str: The environment variable value
    """
    value = os.getenv(key, default)
    if required and not value:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return value

def get_neo4j_config() -> Dict[str, str]:
    """
    Returns Neo4j vector store config pulled from environment or safe defaults.

    Raises:
        EnvironmentError: if any required variable is missing and no default is provided.

    Returns:
        Dict[str, str]: A validated configuration dictionary.
    """
    default_logger.info("Fetching neo4j configs...")
    return {
        "url": get_env_var("NEO4J_URI", required=True),
        "username": get_env_var("NEO4J_USERNAME", required=True),
        "password": get_env_var("NEO4J_PASSWORD", required=True),
        "index_name": get_env_var("NEO4J_INDEX_NAME", DEFAULT_INDEX_NAME),
        "node_label": get_env_var("NEO4J_NODE_LABEL", DEFAULT_NODE_LABEL),
        "text_property": get_env_var("NEO4J_TEXT_PROPERTY", DEFAULT_TEXT_PROPERTY),
        "embedding_property": get_env_var("NEO4J_EMBEDDING_PROPERTY", DEFAULT_EMBEDDING_PROPERTY),
    }
