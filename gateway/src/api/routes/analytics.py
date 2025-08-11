"""
API routes for analytics screen in mcp-client auditor data
"""

from fastapi import APIRouter, Depends
from api.dependencies import require_roles
from core.models.user import UserInDB


@router.get("/analytics")
async def auditor_dashboard(current_user: UserInDB = Depends(require_roles("auditor"))):
    """
    Analytics for auditor users only though superadmin/admin roles can also access this .
    """
    ...
