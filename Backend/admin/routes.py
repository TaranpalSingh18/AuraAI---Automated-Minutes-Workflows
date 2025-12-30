
"""
AdminPerspective API routes - Assign tasks to employees via Trello
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from bson import ObjectId
from typing import List, Optional, Dict, Any
import asyncio
import logging

from auth.auth_routes import get_current_user
from admin.trello_service import AdminTrelloService, set_database as set_admin_trello_database

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Database instance (will be set by main.py)
database = None


def set_database(db):
    global database
    database = db
    # Also set it for admin trello service (if that file expects DB hook)
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
    Assign a task based on a natural language query.
    Uses AdminTrelloService to parse the query and to create lists/cards/checklists/checkitems.
    Only users with persona 'admin' may use this endpoint.
    """

    # auth: admin only
    if current_user.get("persona") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can use this endpoint")

    if not request.query or not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    # ensure DB initialized (we use it to fetch user list for parser)
    if database is None:
        raise HTTPException(status_code=500, detail="Database not initialized. Please restart the server.")

    # fetch the admin user's saved settings (for gemini key or default board id)
    user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
    gemini_api_key = user.get("settings", {}).get("gemini_api_key", "").strip()

    # determine board id: request takes precedence, then user settings 'workspace_id'
    board_id = request.board_id or user.get("settings", {}).get("workspace_id")
    if not board_id:
        raise HTTPException(status_code=400, detail="Board ID is required (provide board_id or set workspace_id in Settings)")

    # # list name to place the user's card (default)
    # list_name = request.list_name or "To Do"
    # checklist_name = "Tasks"

    try:
        # gather available users from DB to help parser match names (best-effort)
        try:
            db_users = await database.users.find({}, {"name": 1}).to_list(length=1000)
            available_users = [u.get("name") for u in db_users if u.get("name")]
        except Exception:
            # If DB read fails for some reason, fallback to empty list
            available_users = []

        # instantiate service (synchronous blocking code)
        service = AdminTrelloService(board_id=board_id, gemini_api_key=gemini_api_key or None)

        # parse assignment using service.parse_task_assignment (may use LLM or heuristics)
        parsed = await asyncio.to_thread(service.parse_task_assignment, request.query, available_users)
        employee_name = parsed.get("employee_name", "").strip()
        task_description = parsed.get("task_description", "").strip()

        if not task_description:
            raise HTTPException(status_code=400, detail="Could not determine task description from query")

        # if employee name is empty, try to fallback: if only one available user, pick them
        if not employee_name:
            if len(available_users) == 1:
                employee_name = available_users[0]
            else:
                # allow admin to create card for a name provided inline even if not in DB
                # you can opt to require matching users; here we allow it but warn
                # return helpful error asking for explicit employee if needed
                raise HTTPException(status_code=400, detail="Could not determine employee name from query. Mention the employee explicitly.")

        # perform the assignment on a thread (blocking network calls)
        result = await asyncio.to_thread(
            service.assign_task_to_user,
            employee_name,        # user_name
            task_description,     # task_text
            None,                 # board_list_name → auto "{User}'s Todo"
            True,                 # create list if missing
            True,                 # create card per task
            None                  # no checklist
        )


        return AssignTaskResponse(
            success=bool(result.get("success")),
            message=result.get("message", "Assigned task"),
            employee_name=employee_name,
            task_description=task_description
        )

    except HTTPException:
        # re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.exception("Error in assign_task_to_employee")
        raise HTTPException(status_code=500, detail=f"Error processing assignment: {str(e)}")










# iske niche uncomment karo 
# """
# AdminPerspective API routes - Assign tasks to employees via Trello
# """
# from fastapi import APIRouter, HTTPException, Depends
# from fastapi.security import HTTPBearer
# from pydantic import BaseModel
# from bson import ObjectId
# from typing import List, Optional

# from auth.auth_routes import get_current_user
# from admin.trello_service import AdminTrelloService, set_database as set_admin_trello_database
# from sigmoyd.sigmoyd_trello import process_query

# # Database instance (will be set by main.py)
# database = None

# def set_database(db):
#     global database
#     database = db
#     # Also set it for admin trello service
#     set_admin_trello_database(db)

# router = APIRouter(prefix="/admin", tags=["admin"])
# security = HTTPBearer()


# class AssignTaskRequest(BaseModel):
#     query: str
#     workspace_id: Optional[str] = None
#     board_id: Optional[str] = None
#     list_name: Optional[str] = None


# class AssignTaskResponse(BaseModel):
#     success: bool
#     message: str
#     employee_name: Optional[str] = None
#     task_description: Optional[str] = None


# @router.post("/assign-task", response_model=AssignTaskResponse)
# async def assign_task_to_employee(
#     request: AssignTaskRequest,
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Process query using sigmoyd trello operations.
#     The query is passed to sigmoyd_trello.py and the output is returned.
#     Only admins can use this endpoint
#     """
#     # Check if user is admin
#     if current_user.get("persona") != "admin":
#         raise HTTPException(status_code=403, detail="Only admins can use this endpoint")
    
#     if not request.query.strip():
#         raise HTTPException(status_code=400, detail="Query cannot be empty")
    
#     # Check if database is initialized
#     if database is None:
#         raise HTTPException(
#             status_code=500,
#             detail="Database not initialized. Please restart the server."
#         )
    
#     # Get user settings
#     user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
#     composio_api_key = user.get("settings", {}).get("composio_api_key", "").strip()
#     gemini_api_key = user.get("settings", {}).get("gemini_api_key", "").strip()
    
#     if not composio_api_key:
#         raise HTTPException(
#             status_code=400,
#             detail="Composio API key not configured. Please add it in Settings."
#         )
    
#     if not gemini_api_key:
#         raise HTTPException(
#             status_code=400,
#             detail="Gemini API key not configured. Please add it in Settings."
#         )
    
#     try:
#         # Process query using sigmoyd trello
#         result = await process_query(
#             query=request.query,
#             composio_api_key_param=composio_api_key,
#             gemini_api_key_param=gemini_api_key
#         )
        
#         if result.get("success"):
#             # Format the output message
#             output = result.get("output", "")
#             if result.get("errors"):
#                 output += f"\n\nErrors:\n{result.get('errors')}"
            
#             return AssignTaskResponse(
#                 success=True,
#                 message=output,
#                 employee_name=None,
#                 task_description=None
#             )
#         else:
#             error_msg = result.get("error", "Unknown error")
#             output = result.get("output", "")
#             if output:
#                 error_msg = f"{output}\n\nError: {error_msg}"
            
#             return AssignTaskResponse(
#                 success=False,
#                 message=error_msg,
#                 employee_name=None,
#                 task_description=None
#             )
            
#     except Exception as e:
#         import traceback
#         error_trace = traceback.format_exc()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error processing query: {str(e)}\n\nTraceback:\n{error_trace}"
#         )

