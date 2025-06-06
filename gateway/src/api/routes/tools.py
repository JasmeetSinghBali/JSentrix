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

router = APIRouter()

MCP_SERVER_URL = f"http://{settings.MCP_SERVER_HOST}:{settings.MCP_SERVER_PORT}"


@router.get("/listtools")
async def list_tools(
    current_user: UserInDB = Depends(require_roles("superadmin", "superuser", "admin"))
):
    """
    List available tools (protected superadmin only)
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
    """
    mcp_url = f"{MCP_SERVER_URL}/tools/{tool_name}/invoke"
    async with httpx.AsyncClient() as client:
        resp = await client.post(mcp_url, json=req)
        if resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=f"Tool invocation failed: {resp.text}",
            )
        return resp.json()
