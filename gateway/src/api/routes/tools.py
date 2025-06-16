"""
gateway/src/api/routes/tools
API routes for tool listing and invocation, protected by authentication.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from api.dependencies import require_roles
from core.models.user import UserInDB
from core.config.settings import settings
import httpx
from typing import TypedDict
from infrastructure.jsonrpc.jsonrpc_client import JsonRpcClient

router = APIRouter()

MCP_SERVER_URL = f"http://{settings.MCP_SERVER_HOST}:{settings.MCP_SERVER_PORT}"
MCP_JSONRPC_URL = f"{MCP_SERVER_URL}/jsonrpc"
mcp_jsonrpc = JsonRpcClient(MCP_JSONRPC_URL)


@router.get("/listtools")
async def list_tools(
    current_user: UserInDB = Depends(require_roles("superadmin", "superuser", "admin"))
):
    """
    List available tools (protected superadmin only)
    Uses REST-to-REST for backward compatibility with MCP server.
    """
    mcp_url = f"{MCP_SERVER_URL}/list_tools"
    async with httpx.AsyncClient() as client:
        resp = await client.get(mcp_url)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Failed to fetch tools from MCP server",
            )
        return resp.json()


class ToolInvokeRequest(TypedDict, total=False):
    arguments: dict


@router.post("/tools/{tool_name}/invoke")
async def invoke_tool(
    tool_name: str,
    req: ToolInvokeRequest,
    current_user: UserInDB = Depends(require_roles("superadmin", "superuser", "admin")),
):
    """
    Invoke a tool (protected superadmin only)
    REST-in, JSON-RPC-out to MCP server.
    """
    try:
        # Use JSON-RPC for backend comm, keep REST for client
        result = await mcp_jsonrpc.call(tool_name, req.get("arguments", {}))
        return {"result": result}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Tool invocation failed: {str(e)}",
        )
