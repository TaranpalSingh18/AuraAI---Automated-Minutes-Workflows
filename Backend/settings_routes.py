from fastapi import APIRouter, HTTPException, Depends
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from bson import ObjectId
from typing import Optional

from auth.auth_routes import get_current_user

# Database will be set from main after initialization
database = None

def set_database(db):
    global database
    database = db

router = APIRouter(prefix="/settings", tags=["settings"])
security = HTTPBearer()


class SettingsUpdate(BaseModel):
    composio_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    workspace_id: Optional[str] = None


@router.put("")
async def update_settings(
    settings: SettingsUpdate,
    current_user: dict = Depends(get_current_user)
):
    """Update user settings (API keys, workspace ID)"""
    user_id = ObjectId(current_user["id"])
    
    # Get current settings
    user = await database.users.find_one({"_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    current_settings = user.get("settings", {})
    if not isinstance(current_settings, dict):
        current_settings = {}
    
    # Track if Composio API key was newly added or changed
    composio_key_changed = False
    old_composio_key = current_settings.get("composio_api_key", "")
    
    # Update only provided fields (and only if they're not empty strings)
    if settings.composio_api_key is not None:
        new_key = settings.composio_api_key.strip() if settings.composio_api_key else ""
        if new_key:  # Only update if key is not empty
            if new_key != old_composio_key:
                composio_key_changed = True
            current_settings["composio_api_key"] = new_key
        elif new_key == "" and old_composio_key:  # Allow clearing the key
            current_settings["composio_api_key"] = ""
            composio_key_changed = True
    
    if settings.gemini_api_key is not None:
        gemini_key = settings.gemini_api_key.strip() if settings.gemini_api_key else ""
        if gemini_key:
            current_settings["gemini_api_key"] = gemini_key
    
    if settings.workspace_id is not None:
        workspace_id = settings.workspace_id.strip() if settings.workspace_id else ""
        if workspace_id:
            current_settings["workspace_id"] = workspace_id
    
    # Update user document - ensure settings field exists
    await database.users.update_one(
        {"_id": user_id},
        {"$set": {"settings": current_settings}}
    )
    
    # Verify the update was successful
    updated_user = await database.users.find_one({"_id": user_id})
    if updated_user:
        current_settings = updated_user.get("settings", {})
    
    # Debug: Log the saved composio_api_key (first 4 and last 4 chars only for security)
    saved_key = current_settings.get("composio_api_key", "")
    if saved_key:
        key_preview = saved_key[:4] + "..." + saved_key[-4:] if len(saved_key) > 8 else "***"
        print(f"DEBUG: Composio API key saved for user {user_id}: {key_preview}")
    else:
        print(f"DEBUG: No Composio API key found in settings for user {user_id}")
    
    response_data = {"message": "Settings updated successfully", "settings": current_settings}
    
    # If Composio API key was changed/added, initiate Trello OAuth
    if composio_key_changed:
        try:
            from composio_auth import initiate_trello_connection
            oauth_result = initiate_trello_connection(api_key=current_settings["composio_api_key"])
            response_data["composio_oauth"] = {
                "redirect_url": oauth_result["redirect_url"],
                "connected_account_id": oauth_result["connected_account_id"],
                "connection_status": oauth_result["connection_status"],
                "requires_auth": oauth_result["connection_status"] != "ACTIVE"
            }
        except Exception as e:
            # Don't fail the settings update if OAuth initiation fails
            response_data["composio_oauth"] = {
                "error": f"Failed to initiate Trello OAuth: {str(e)}"
            }
    
    return response_data


@router.get("")
async def get_settings(current_user: dict = Depends(get_current_user)):
    """Get current user settings and Trello connection status"""
    user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    settings = user.get("settings", {})
    if not isinstance(settings, dict):
        settings = {}
    
    response = {
        "composio_api_key": settings.get("composio_api_key", ""),
        "gemini_api_key": settings.get("gemini_api_key", ""),
        "workspace_id": settings.get("workspace_id", "")
    }
    
    # Check Trello connection status if Composio API key exists
    composio_api_key = settings.get("composio_api_key", "")
    if composio_api_key:
        composio_api_key = composio_api_key.strip()
    if composio_api_key:
        try:
            from composio_auth import check_trello_connection
            connection_status = check_trello_connection(api_key=composio_api_key)
            response["trello_connection"] = connection_status
        except Exception as e:
            response["trello_connection"] = {
                "is_connected": False,
                "error": str(e)
            }
    else:
        response["trello_connection"] = {
            "is_connected": False,
            "error": "Composio API key not configured"
        }
    
    return response

