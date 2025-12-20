"""
AdminPerspective API routes - Assign tasks to employees via Trello
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from bson import ObjectId
from typing import List, Optional

from auth.auth_routes import get_current_user
from admin.trello_service import AdminTrelloService, set_database as set_admin_trello_database
from sigmoyd.sigmoyd_trello import process_query

# Database instance (will be set by main.py)
database = None

def set_database(db):
    global database
    database = db
    # Also set it for admin trello service
    set_admin_trello_database(db)

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBearer()


class AssignTaskRequest(BaseModel):
    query: str
    workspace_id: Optional[str] = None
    board_id: Optional[str] = None
    list_name: Optional[str] = None


class AssignTaskResponse(BaseModel):
    success: bool
    message: str
    employee_name: Optional[str] = None
    task_description: Optional[str] = None


@router.post("/assign-task", response_model=AssignTaskResponse)
async def assign_task_to_employee(
    request: AssignTaskRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Process query using sigmoyd trello operations.
    The query is passed to sigmoyd_trello.py and the output is returned.
    Only admins can use this endpoint
    """
    # Check if user is admin
    if current_user.get("persona") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can use this endpoint")
    
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    
    # Check if database is initialized
    if database is None:
        raise HTTPException(
            status_code=500,
            detail="Database not initialized. Please restart the server."
        )
    
    # Get user settings
    user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
    composio_api_key = user.get("settings", {}).get("composio_api_key", "").strip()
    gemini_api_key = user.get("settings", {}).get("gemini_api_key", "").strip()
    
    if not composio_api_key:
        raise HTTPException(
            status_code=400,
            detail="Composio API key not configured. Please add it in Settings."
        )
    
    if not gemini_api_key:
        raise HTTPException(
            status_code=400,
            detail="Gemini API key not configured. Please add it in Settings."
        )
    
    try:
        # Process query using sigmoyd trello
        result = await process_query(
            query=request.query,
            composio_api_key_param=composio_api_key,
            gemini_api_key_param=gemini_api_key
        )
        
        if result.get("success"):
            # Format the output message
            output = result.get("output", "")
            if result.get("errors"):
                output += f"\n\nErrors:\n{result.get('errors')}"
            
            return AssignTaskResponse(
                success=True,
                message=output,
                employee_name=None,
                task_description=None
            )
        else:
            error_msg = result.get("error", "Unknown error")
            output = result.get("output", "")
            if output:
                error_msg = f"{output}\n\nError: {error_msg}"
            
            return AssignTaskResponse(
                success=False,
                message=error_msg,
                employee_name=None,
                task_description=None
            )
            
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        raise HTTPException(
            status_code=500,
            detail=f"Error processing query: {str(e)}\n\nTraceback:\n{error_trace}"
        )

