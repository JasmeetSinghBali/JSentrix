"""
API routes for dashboard auditor data
"""

from fastapi import APIRouter, Depends
from api.dependencies import require_roles
from core.models.user import UserInDB


@router.get("/dashboard")
async def auditor_dashboard(current_user: UserInDB = Depends(require_roles("auditor"))):
    """
    Dashboard for auditor users only.
    """
    ...
