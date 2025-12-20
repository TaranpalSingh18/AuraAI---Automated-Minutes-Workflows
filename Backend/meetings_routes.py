from fastapi import APIRouter, HTTPException, Depends, UploadFile, File
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from bson import ObjectId
from datetime import datetime
from typing import List, Optional

from auth.auth_routes import get_current_user
from meetings_service import process_transcript_with_gemini
from automations.meeting_task_converter import MeetingTaskConverter

# Database will be set from main after initialization
database = None

def set_database(db):
    global database
    database = db

router = APIRouter(prefix="/meetings", tags=["meetings"])
security = HTTPBearer()


class MeetingResponse(BaseModel):
    id: str
    title: str
    date: str
    participants: List[str]
    summary: str
    transcript_text: str
    action_items: List[dict]
    created_by: str
    workspace_id: Optional[str] = None


@router.post("/upload")
async def upload_transcript(
    file: UploadFile = File(...),
    workspace_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Upload and process meeting transcript (Admin only)"""
    # Check if user is admin
    if current_user.get("persona") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can upload transcripts")
    
    # Get Gemini API key from user settings
    user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
    gemini_api_key = user.get("settings", {}).get("gemini_api_key")
    
    if not gemini_api_key:
        raise HTTPException(
            status_code=400, 
            detail="Gemini API key not configured. Please add it in Settings."
        )
    
    # Trim whitespace from API key
    gemini_api_key = gemini_api_key.strip()
    
    # Check file type
    if not file.filename.endswith('.docx'):
        raise HTTPException(status_code=400, detail="Only .docx files are supported")
    
    # Read file content
    file_content = await file.read()
    
    try:
        # Process transcript with Gemini
        processed_data = process_transcript_with_gemini(file_content, gemini_api_key)
        
        # Extract title from summary
        title = processed_data["summary"].split("\n")[0].replace("(TITLE)", "").strip()
        if not title or title.startswith("Participants"):
            title = f"Meeting - {datetime.utcnow().strftime('%Y-%m-%d')}"
        
        # Create meeting document
        meeting_data = {
            "title": title,
            "date": datetime.utcnow(),
            "participants": processed_data["participants"],
            "summary": processed_data["summary"],
            "transcript_text": processed_data["transcript_text"],
            "action_items": processed_data["action_items"],
            "created_by": current_user["id"],
            "workspace_id": workspace_id,
            "created_at": datetime.utcnow()
        }
        
        result = await database.meetings.insert_one(meeting_data)
        meeting_id = str(result.inserted_id)
        
        return {
            "id": meeting_id,
            "message": "Transcript processed successfully",
            "meeting": {
                "id": meeting_id,
                "title": title,
                "participants": processed_data["participants"],
                "action_items_count": len(processed_data["action_items"])
            }
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing transcript: {str(e)}")


@router.get("", response_model=List[MeetingResponse])
async def get_meetings(
    workspace_id: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Get all meetings (filtered by workspace if provided)"""
    query = {}
    if workspace_id:
        query["workspace_id"] = workspace_id
    
    # Employees can only see meetings in their workspace
    if current_user.get("persona") == "employee":
        user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
        user_workspace = user.get("settings", {}).get("workspace_id")
        if user_workspace:
            query["workspace_id"] = user_workspace
        elif not workspace_id:
            # Employee without workspace - return empty
            return []
    
    meetings = []
    async for meeting in database.meetings.find(query).sort("date", -1):
        meeting["id"] = str(meeting["_id"])
        del meeting["_id"]
        if isinstance(meeting.get("date"), datetime):
            meeting["date"] = meeting["date"].isoformat()
        meetings.append(meeting)
    
    return meetings


@router.get("/{meeting_id}", response_model=MeetingResponse)
async def get_meeting(
    meeting_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get meeting by ID"""
    try:
        meeting = await database.meetings.find_one({"_id": ObjectId(meeting_id)})
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
        
        # Employees can only access meetings in their workspace
        if current_user.get("persona") == "employee":
            user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
            user_workspace = user.get("settings", {}).get("workspace_id")
            if meeting.get("workspace_id") != user_workspace:
                raise HTTPException(status_code=403, detail="Access denied to this meeting")
        
        meeting["id"] = str(meeting["_id"])
        del meeting["_id"]
        if isinstance(meeting.get("date"), datetime):
            meeting["date"] = meeting["date"].isoformat()
        
        return meeting
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=400, detail=f"Invalid meeting ID: {str(e)}")


class ConvertToTaskRequest(BaseModel):
    participant_name: str
    task_text: str
    deadline: Optional[str] = None


class ConvertToTaskResponse(BaseModel):
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None
    list_id: Optional[str] = None
    card_id: Optional[str] = None
    checklist_id: Optional[str] = None


@router.post("/{meeting_id}/convert-to-task", response_model=ConvertToTaskResponse)
async def convert_action_item_to_task(
    meeting_id: str,
    request: ConvertToTaskRequest,
    current_user: dict = Depends(get_current_user)
):
    """
    Convert an action item from a meeting to a Trello task
    Creates/uses participant's Todo list and adds task to checklist
    Admin only
    """
    # Check if user is admin
    if current_user.get("persona") != "admin":
        raise HTTPException(status_code=403, detail="Only admins can convert action items to tasks")
    
    # Get user settings
    user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
    composio_api_key = user.get("settings", {}).get("composio_api_key", "").strip()
    board_id = user.get("settings", {}).get("workspace_id", "").strip()
    
    if not composio_api_key:
        raise HTTPException(
            status_code=400,
            detail="Composio API key not configured. Please add it in Settings."
        )
    
    if not board_id:
        raise HTTPException(
            status_code=400,
            detail="Trello board ID not configured. Please configure it in Settings."
        )
    
    # Verify meeting exists and user has access
    try:
        meeting = await database.meetings.find_one({"_id": ObjectId(meeting_id)})
        if not meeting:
            raise HTTPException(status_code=404, detail="Meeting not found")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid meeting ID: {str(e)}")
    
    try:
        # Initialize converter
        converter = MeetingTaskConverter(composio_api_key)
        
        # Convert action item to task
        result = converter.convert_action_item_to_task(
            board_id=board_id,
            participant_name=request.participant_name,
            task_text=request.task_text,
            deadline=request.deadline
        )
        
        if result.get("success"):
            return ConvertToTaskResponse(
                success=True,
                message=result.get("message", "Task converted successfully"),
                list_id=result.get("list_id"),
                card_id=result.get("card_id"),
                checklist_id=result.get("checklist_id")
            )
        else:
            return ConvertToTaskResponse(
                success=False,
                error=result.get("error", "Unknown error occurred")
            )
    
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in convert_action_item_to_task: {str(e)}")
        print(f"Traceback: {error_trace}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to convert action item to task: {str(e)}"
        )

