"""
mcp_server/utils/serialize_exception.py
"""

import traceback
from .logger import get_logger

logger = get_logger("serialize_exception.mcpserver")


def serialize_error(e: Exception) -> dict:
    """
    Serialize python exception into dict ready to transport to external counterparts
    with fallback error support in case serialization for exception itself fails
    """
    try:
        logger.debug(f"RAW TRACEBACK: {traceback.format_exc()}")
        return {
            "error_type": type(e).__name__,
            "message": str(e),
            "details": repr(e),
        }
    except Exception as fallback_error:
        logger.error(f"Error while serializing exception: {str(fallback_error)}")
        return {
            "error_type": "SerializationError",
            "message": "Failed to serialize original exception.",
            "details": f"Fallback error: {repr(fallback_error)}",
        }
