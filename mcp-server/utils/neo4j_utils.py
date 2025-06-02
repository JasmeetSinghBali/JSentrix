"""
utils/neo4j_utils.py

Neo4j configuration and driver pooling utilities with async support.
"""

import os
import asyncio
from typing import Dict, Optional

from dotenv import load_dotenv

from .logger import get_logger
from .lifecycle import register_shutdown_callback

logger = get_logger("jsentrix")

load_dotenv()

DEFAULT_INDEX_NAME = "compliance_clauses"
DEFAULT_NODE_LABEL = "ComplianceClause"
DEFAULT_TEXT_PROPERTY = "text"
DEFAULT_EMBEDDING_PROPERTY = "embedding"

_neo4j_config: Optional[Dict[str, str]] = None


def get_env_var(key: str, default: str = None, required: bool = False) -> str:
    """
    Fetches an environment variable, with support for defaults and required flag.
    """
    value = os.getenv(key, default)
    if required and not value:
        raise EnvironmentError(f"Missing required environment variable: {key}")
    return value


def get_neo4j_config() -> Dict[str, str]:
    """
    Loads and caches Neo4j configuration from environment variables.
    """
    global _neo4j_config
    if _neo4j_config is None:
        logger.debug("Initializing Neo4j config...")
        _neo4j_config = {
            "url": get_env_var("NEO4J_URI", required=True),
            "username": get_env_var("NEO4J_USERNAME", required=True),
            "password": get_env_var("NEO4J_PASSWORD", required=True),
            "index_name": get_env_var("NEO4J_INDEX_NAME", DEFAULT_INDEX_NAME),
            "node_label": get_env_var("NEO4J_NODE_LABEL", DEFAULT_NODE_LABEL),
            "text_property": get_env_var("NEO4J_TEXT_PROPERTY", DEFAULT_TEXT_PROPERTY),
            "embedding_property": get_env_var(
                "NEO4J_EMBEDDING_PROPERTY", DEFAULT_EMBEDDING_PROPERTY
            ),
        }
    return _neo4j_config


# --- for Sync driver pooling ---
from neo4j import GraphDatabase, Driver

_neo4j_driver: Optional[Driver] = None


def get_neo4j_driver() -> Driver:
    """
    Returns a singleton Neo4j driver instance, initializing if necessary.
    Registers a shutdown callback to close the driver on app exit.
    """
    global _neo4j_driver
    if _neo4j_driver is None:
        config = get_neo4j_config()
        logger.debug("Initializing Neo4j driver...")
        _neo4j_driver = GraphDatabase.driver(
            config["url"], auth=(config["username"], config["password"])
        )

        # Register shutdown callback for neo4j once
        def close_driver():
            global _neo4j_driver
            if _neo4j_driver is not None:
                logger.info("Closing Neo4j driver...")
                _neo4j_driver.close()
                _neo4j_driver = None

        register_shutdown_callback(close_driver)
    return _neo4j_driver


def close_neo4j_driver():
    """
    Explicitly closes the Neo4j driver (for testing or script use).
    """
    global _neo4j_driver
    if _neo4j_driver is not None:
        logger.info("Explicitly closing Neo4j driver...")
        _neo4j_driver.close()
        _neo4j_driver = None


# --- Async Driver Pooling ---
try:
    from neo4j.async_driver import AsyncDriver, AsyncGraphDatabase
except ImportError:
    AsyncDriver = None
    AsyncGraphDatabase = None

# forward refferences "AsyncDriver" in case import error
# reff: https://peps.python.org/pep-0484/#forward-references
_neo4j_async_driver: Optional["AsyncDriver"] = None


def get_async_neo4j_driver() -> "AsyncDriver":
    """
    Returns a singleton async Neo4j driver instance, initializing if necessary.
    Registers a shutdown callback to close the driver on app exit.
    """
    global _neo4j_async_driver
    if AsyncGraphDatabase is None:
        raise ImportError(
            "neo4j[async] is not installed. Please install the async extra."
        )
    if _neo4j_async_driver is None:
        config = get_neo4j_config()
        logger.debug("Initializing async Neo4j driver...")
        _neo4j_async_driver = AsyncGraphDatabase.driver(
            config["url"],
            auth=(config["username"], config["password"]),
            max_connection_pool_size=20,  # Tune as needed
            connection_acquisition_timeout=30,
        )

        async def close_async_driver():
            global _neo4j_async_driver
            if _neo4j_async_driver is not None:
                logger.info("Closing async Neo4j driver...")
                try:
                    await _neo4j_async_driver.close()
                except Exception as e:
                    logger.error(f"Error closing async driver: {str(e)}")
                _neo4j_async_driver = None

        register_shutdown_callback(close_async_driver)
    return _neo4j_async_driver


def close_async_neo4j_driver():
    """
    Explicitly closes the async Neo4j driver (for testing or script use).
    """
    global _neo4j_async_driver
    if _neo4j_async_driver is not None:
        logger.info("Explicitly closing async Neo4j driver...")
        asyncio.run(_neo4j_async_driver.close())
        _neo4j_async_driver = None
