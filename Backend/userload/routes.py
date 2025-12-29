"""
UserLoad API routes - Fetch and manage user tasks from Trello (Direct API)
"""
from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from bson import ObjectId
from typing import List, Optional, Dict, Any

from auth.auth_routes import get_current_user
from userload.trello_service import UserLoadTrelloService, database

router = APIRouter(prefix="/userload", tags=["userload"])
security = HTTPBearer()

# --- Database hook (required by main.py) ---
database = None

def set_database(db):
    global database
    database = db


# ---------- RESPONSE MODELS ----------

class TaskResponse(BaseModel):
    id: str
    name: str
    state: str
    checklist_id: str


class FetchTasksResponse(BaseModel):
    tasks: List[TaskResponse]


class UpdateTaskRequest(BaseModel):
    board_id: str
    task_id: str
    checklist_id: str
    completed: bool


class UpdateTaskResponse(BaseModel):
    success: bool
    message: str


# ---------- FETCH TASKS ----------

@router.get("/tasks", response_model=FetchTasksResponse)
async def fetch_user_tasks(
    board_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """
    Fetch checklist tasks from "{User}'s Todo" card
    """

    if not board_id:
        raise HTTPException(
            status_code=400,
            detail="board_id is required"
        )

    user_name = current_user.get("name", "User")

    try:
        service = UserLoadTrelloService(board_id=board_id)
        tasks = service.get_user_tasks(user_name)

        return FetchTasksResponse(
            tasks=[
                TaskResponse(
                    id=t["id"],
                    name=t["name"],
                    state=t["state"],
                    checklist_id=t["checklist_id"]
                )
                for t in tasks
            ]
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ---------- UPDATE TASK STATUS ----------

@router.post("/update-task", response_model=UpdateTaskResponse)
async def update_task_status(
    request: UpdateTaskRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Mark checklist item complete / incomplete
    """

    try:
        service = UserLoadTrelloService(board_id=request.board_id)

        service.update_task_status(
            card_id=f"{current_user.get('name', 'User')}'s Todo",  # logical reference
            checklist_id=request.checklist_id,
            checkitem_id=request.task_id,
            completed=request.completed
        )

        return UpdateTaskResponse(
            success=True,
            message="Task updated successfully"
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )







# iske niche uncomment karo 
# """
# UserLoad API routes - Fetch and manage user tasks from Trello
# """
# from fastapi import APIRouter, HTTPException, Depends
# from fastapi.security import HTTPBearer
# from pydantic import BaseModel
# from bson import ObjectId
# from typing import List, Optional, Dict, Any

# from auth.auth_routes import get_current_user
# from userload.trello_service import UserLoadTrelloService, set_database, database

# router = APIRouter(prefix="/userload", tags=["userload"])
# security = HTTPBearer()


# class TaskResponse(BaseModel):
#     id: str
#     name: str
#     state: str
#     checklist_id: str


# class FetchTasksResponse(BaseModel):
#     tasks: List[TaskResponse]


# class UpdateTaskRequest(BaseModel):
#     query: str
#     workspace_id: Optional[str] = None
#     board_id: Optional[str] = None


# class UpdateTaskResponse(BaseModel):
#     success: bool
#     message: str
#     updated_tasks: List[Dict[str, Any]]


# @router.get("/tasks", response_model=FetchTasksResponse)
# async def fetch_user_tasks(
#     workspace_id: Optional[str] = None,
#     board_id: Optional[str] = None,
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Fetch user's pending tasks from Trello
#     Looks for card named "{user_name}'s Todo" in the workspace/board
#     """
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
    
#     # Get workspace_id from settings if not provided
#     if not workspace_id:
#         workspace_id = user.get("settings", {}).get("workspace_id")
    
#     if not workspace_id:
#         raise HTTPException(
#             status_code=400,
#             detail="Workspace ID not configured. Please add it in Settings."
#         )
    
#     if not board_id:
#         raise HTTPException(
#             status_code=400,
#             detail="Board ID is required. Please provide board_id parameter."
#         )
    
#     user_name = current_user.get("name", "User")
    
#     try:
#         service = UserLoadTrelloService(
#             composio_api_key=composio_api_key,
#             gemini_api_key=gemini_api_key
#         )
        
#         tasks = service.get_user_tasks(workspace_id, board_id, user_name)
        
#         return FetchTasksResponse(
#             tasks=[
#                 TaskResponse(
#                     id=task["id"],
#                     name=task["name"],
#                     state=task["state"],
#                     checklist_id=task["checklist_id"]
#                 )
#                 for task in tasks
#             ]
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error fetching tasks: {str(e)}"
#         )


# @router.post("/update-task", response_model=UpdateTaskResponse)
# async def update_task_status(
#     request: UpdateTaskRequest,
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Update task status using natural language query
#     Example: "Mark task 1 as complete" or "Uncheck the first task"
#     """
#     if not request.query.strip():
#         raise HTTPException(status_code=400, detail="Query cannot be empty")
    
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
    
#     # Get workspace_id and board_id
#     workspace_id = request.workspace_id or user.get("settings", {}).get("workspace_id")
#     board_id = request.board_id
    
#     if not workspace_id:
#         raise HTTPException(
#             status_code=400,
#             detail="Workspace ID not configured. Please add it in Settings."
#         )
    
#     if not board_id:
#         raise HTTPException(
#             status_code=400,
#             detail="Board ID is required."
#         )
    
#     user_name = current_user.get("name", "User")
    
#     try:
#         service = UserLoadTrelloService(
#             composio_api_key=composio_api_key,
#             gemini_api_key=gemini_api_key
#         )
        
#         # First, get current tasks
#         tasks = service.get_user_tasks(workspace_id, board_id, user_name)
#         if not tasks:
#             return UpdateTaskResponse(
#                 success=False,
#                 message="No tasks found. Please ensure your Todo card exists in Trello.",
#                 updated_tasks=[]
#             )
        
#         # Get card ID
#         card_id = service.get_user_todo_card_id(workspace_id, board_id, user_name)
#         if not card_id:
#             return UpdateTaskResponse(
#                 success=False,
#                 message=f"Could not find card '{user_name}'s Todo' in the board.",
#                 updated_tasks=[]
#             )
        
#         # Parse natural language query
#         update_actions = service.parse_natural_language_task_update(request.query, tasks)
        
#         if not update_actions:
#             return UpdateTaskResponse(
#                 success=False,
#                 message="Could not understand which tasks to update. Please be more specific.",
#                 updated_tasks=[]
#             )
        
#         # Execute updates
#         updated_tasks = []
#         for action_item in update_actions:
#             completed = action_item["action"] == "check"
#             success = service.update_task_status(
#                 card_id=card_id,
#                 checklist_id=action_item["checklist_id"],
#                 checkitem_id=action_item["task_id"],
#                 completed=completed
#             )
            
#             if success:
#                 # Find task name
#                 task = next((t for t in tasks if t["id"] == action_item["task_id"]), None)
#                 updated_tasks.append({
#                     "task_id": action_item["task_id"],
#                     "task_name": task["name"] if task else "Unknown",
#                     "action": action_item["action"],
#                     "success": True
#                 })
        
#         if updated_tasks:
#             return UpdateTaskResponse(
#                 success=True,
#                 message=f"Successfully updated {len(updated_tasks)} task(s).",
#                 updated_tasks=updated_tasks
#             )
#         else:
#             return UpdateTaskResponse(
#                 success=False,
#                 message="Failed to update tasks. Please try again.",
#                 updated_tasks=[]
#             )
            
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Error updating tasks: {str(e)}"
#         )

