
"""
Composio OAuth routes - handle Trello authentication via Composio
Clean, production-ready version that relies on composio_auth.py helper functions.
Replace your existing Backend/composio_routes.py with this file.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from fastapi.security import HTTPBearer
from pydantic import BaseModel
from bson import ObjectId
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import os

load_dotenv()

from auth.auth_routes import get_current_user
from composio_auth import (
    initiate_trello_connection,
    check_trello_connection,
    get_trello_boards,
    get_trello_cards,
    disconnect_trello,
)

# Database will be set from main after initialization
database = None

def set_database(db):
    global database
    database = db

router = APIRouter(prefix="/composio", tags=["composio"])
security = HTTPBearer()


class InitiateConnectionResponse(BaseModel):
    redirect_url: Optional[str] = None
    connected_account_id: Optional[str] = None
    connection_status: Optional[str] = None


class ConnectionStatusResponse(BaseModel):
    is_connected: bool
    connection_id: Optional[str] = None
    status: Optional[str] = None
    app_unique_id: Optional[str] = None
    error: Optional[str] = None


class BoardInfo(BaseModel):
    id: str
    name: str
    url: Optional[str] = None
    closed: Optional[bool] = False
    organization: Optional[str] = None


class BoardsResponse(BaseModel):
    boards: List[BoardInfo]
    count: int
    error: Optional[str] = None
    note: Optional[str] = None


class CardInfo(BaseModel):
    id: str
    name: str
    desc: Optional[str] = None
    closed: bool = False
    shortUrl: Optional[str] = None
    url: Optional[str] = None
    dateLastActivity: Optional[str] = None
    due: Optional[str] = None
    dueComplete: bool = False
    list_id: Optional[str] = None
    list_name: Optional[str] = None
    comments_count: int = 0
    badges: Optional[Dict[str, Any]] = None
    labels: Optional[List[Dict[str, Any]]] = None
    members: Optional[List[str]] = None
    checklists_count: int = 0


class CardsResponse(BaseModel):
    cards: List[CardInfo]
    count: int


@router.post("/trello/initiate", response_model=InitiateConnectionResponse)
async def initiate_trello_auth(
    redirect_url: Optional[str] = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """
    Initiate Trello OAuth connection via Composio
    Returns a redirect URL that the user needs to visit to authorize Trello
    """
    user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    settings = user.get("settings", {}) if isinstance(user.get("settings", {}), dict) else {}
    composio_api_key = settings.get("composio_api_key", "")
    if composio_api_key:
        composio_api_key = composio_api_key.strip()

    if not composio_api_key:
        raise HTTPException(status_code=400, detail="Composio API key not configured. Please add it in Settings first.")

    try:
        res = initiate_trello_connection(api_key=composio_api_key, redirect_url=redirect_url)
        return InitiateConnectionResponse(
            redirect_url=res.get("redirect_url"),
            connected_account_id=res.get("connection_request_id") or res.get("connected_account_id"),
            connection_status=res.get("connection_status") or res.get("status"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to initiate Trello connection: {str(e)}")


@router.post("/trello/disconnect")
async def disconnect_trello_endpoint(current_user: dict = Depends(get_current_user)):
    user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    composio_api_key = ""
    try:
        composio_api_key = user.get("settings", {}).get("composio_api_key", "").strip()
    except Exception:
        composio_api_key = ""

    if not composio_api_key:
        raise HTTPException(status_code=400, detail="Composio API key not configured. Please add it in Settings first.")

    try:
        result = disconnect_trello(api_key=composio_api_key)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to disconnect Trello: {str(e)}")


@router.get("/trello/status", response_model=ConnectionStatusResponse)
async def get_trello_connection_status(current_user: dict = Depends(get_current_user)):
    user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    settings = user.get("settings", {}) if isinstance(user.get("settings", {}), dict) else {}
    composio_api_key = settings.get("composio_api_key", "")
    if composio_api_key:
        composio_api_key = composio_api_key.strip()

    if not composio_api_key:
        raise HTTPException(status_code=400, detail="Composio API key not configured. Please add it in Settings first.")

    try:
        res = check_trello_connection(api_key=composio_api_key)
        return ConnectionStatusResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to check Trello connection: {str(e)}")


@router.get("/trello/boards", response_model=BoardsResponse)
async def get_trello_boards_endpoint(current_user: dict = Depends(get_current_user)):
    user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    composio_api_key = user.get("settings", {}).get("composio_api_key", "").strip()
    if not composio_api_key:
        raise HTTPException(status_code=400, detail="Composio API key not configured. Please add it in Settings first.")

    try:
        res = get_trello_boards(api_key=composio_api_key)
        return BoardsResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Trello boards: {str(e)}")


@router.get("/trello/cards", response_model=CardsResponse)
async def get_trello_cards_endpoint(board_id: str = Query(..., description="Trello board ID"), current_user: dict = Depends(get_current_user)):
    user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    settings = user.get("settings", {}) if isinstance(user.get("settings", {}), dict) else {}
    composio_api_key = settings.get("composio_api_key", "")
    if composio_api_key:
        composio_api_key = composio_api_key.strip()

    if not composio_api_key:
        raise HTTPException(status_code=400, detail="Composio API key not configured. Please add it in Settings first.")

    # Get board_id from settings if not provided
    workspace_id = user.get("settings", {}).get("workspace_id")
    if not board_id and workspace_id:
        board_id = workspace_id

    if not board_id:
        raise HTTPException(status_code=400, detail="Board ID is required. Please provide board_id parameter or configure it in Settings.")

    try:
        res = get_trello_cards(api_key=composio_api_key, board_id=board_id)
        return CardsResponse(**res)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch Trello cards: {str(e)}")







# iske niche se pura comment hata do 
# """
# Composio OAuth routes - handle Trello authentication via Composio
# """
# import sys
# from langchain_google_genai import ChatGoogleGenerativeAI
# from fastapi import APIRouter, HTTPException, Depends, Query
# from fastapi.security import HTTPBearer
# from pydantic import BaseModel
# from bson import ObjectId
# # from composio_langchain import ComposioToolSet, Action
# # Add Composio path if it exists (for local development)
# from pathlib import Path
# backend_dir = Path(__file__).parent
# # Try Backend/composio/python first (local repository)
# composio_path = backend_dir / "composio" / "python"
# # Fallback to Model/composio/python if Backend path doesn't exist
# if not composio_path.exists():
#     composio_path = backend_dir.parent / "Model" / "composio" / "python"

# # Try to import Action and App (may not be available in all composio versions)
# Action = None
# App = None
# ComposioToolSet = None

# # PRIORITY 1: Try from installed composio.tools.toolset (most reliable)
# try:
#     from composio.tools.toolset import ComposioToolSet
# except ImportError:
#     # PRIORITY 2: Try from installed composio package
#     try:
#         from composio import ComposioToolSet
#     except ImportError:
#         # PRIORITY 3: Try from composio_langchain (may have version issues)
#         try:
#             from composio_langchain import ComposioToolSet
#         except ImportError:
#             # PRIORITY 4: Fallback to local composio repository (if path exists)
#             if composio_path.exists():
#                 composio_path_str = str(composio_path.resolve())
#                 if composio_path_str not in sys.path:
#                     sys.path.insert(0, composio_path_str)
                
#                 # Remove composio modules to force reimport from local path
#                 removed_modules = {}
#                 modules_to_remove = [key for key in list(sys.modules.keys()) 
#                                     if key.startswith('composio') or key.startswith('plugins.langchain')]
                
#                 for module_name in modules_to_remove:
#                     if 'composio_auth' not in module_name and 'composio_routes' not in module_name:
#                         removed_modules[module_name] = sys.modules[module_name]
#                         del sys.modules[module_name]
                
#                 try:
#                     from plugins.langchain.composio_langchain.toolset import ComposioToolSet
#                 except ImportError:
#                     # Restore modules if import failed
#                     for module_name, module_obj in removed_modules.items():
#                         sys.modules[module_name] = module_obj

# # Try to import Action and App from installed composio
# try:
#     from composio import Action, App
# except ImportError:
#     # Action and App are not used in active code, so we can safely ignore
#     Action = None
#     App = None

# # Try to import NoItemsFound
# try:
#     from composio.client.exceptions import NoItemsFound
# except ImportError:
#     # Fallback if NoItemsFound is not available
#     class NoItemsFound(Exception):
#         pass

# # Fallback: if ComposioToolSet still not available, try from installed packages
# if ComposioToolSet is None:
#     try:
#         from composio.tools.toolset import ComposioToolSet
#     except ImportError:
#         ComposioToolSet = None
# import os
# import asyncio
# import json
# import re
# from typing import Optional, List, Dict, Any
# from dotenv import load_dotenv
# load_dotenv()
# # router=Api
# # gemini_api_key = os.getenv("GEMINI_API_KEY")
# # composio_api_key = os.getenv("COMPOSIO_API_KEY")





# # # --- Environment key loading, sanitizing, and validation (ADD/REPLACE HERE) ---
# # gemini_api_key = os.getenv("GEMINI_API_KEY")

# # # Load and sanitize composio key
# # composio_api_key = os.getenv("COMPOSIO_API_KEY")
# # if composio_api_key:
# #     composio_api_key = composio_api_key.strip()
# #     # masked preview for debugging (first4...last4)
# #     try:
# #         preview = composio_api_key[:4] + "..." + composio_api_key[-4:]
# #     except Exception:
# #         preview = "<could not preview>"
# #     print("COMPOSIO_API_KEY preview:", preview)
# # else:
# #     # Fail early with a clear message so you don't get 'invalid key' later
# #     raise RuntimeError(
# #         "COMPOSIO_API_KEY is not set. Set it in the same shell you run the script from (e.g. $env:COMPOSIO_API_KEY = 'sk_...')."
# #     )

# # # Optional: quick validation of the key by instantiating the client and fetching the entity.
# # # This surfaces 'invalid key' immediately with a helpful message.
# # def _validate_composio_key(key: str) -> None:
# #     try:
# #         ts = ComposioToolSet(api_key=key)
# #         _ = ts.get_entity()  # will raise if key invalid / rejected
# #     except Exception as e:
# #         raise RuntimeError(f"Composio API key appears invalid or rejected by server: {str(e)}")

# # try:
# #     _validate_composio_key(composio_api_key)
# #     print("Composio API key validated successfully.")
# # except Exception as e:
# #     # raise so you see the error immediately and can fix the key
# #     raise RuntimeError(str(e))
# # # -------------------------------------------------------------------------





# from auth.auth_routes import get_current_user
# from composio_auth import initiate_trello_connection, check_trello_connection, get_trello_boards, get_trello_cards, disconnect_trello

# # Database will be set from main after initialization
# database = None

# def set_database(db):
#     global database
#     database = db

# router = APIRouter(prefix="/composio", tags=["composio"])
# security = HTTPBearer()


# class InitiateConnectionResponse(BaseModel):
#     redirect_url: str
#     connected_account_id: str
#     connection_status: str


# class ConnectionStatusResponse(BaseModel):
#     is_connected: bool
#     connection_id: Optional[str] = None
#     status: Optional[str] = None
#     app_unique_id: Optional[str] = None
#     error: Optional[str] = None


# class BoardInfo(BaseModel):
#     id: str
#     name: str
#     url: Optional[str] = None
#     closed: Optional[bool] = False
#     organization: Optional[str] = None


# class BoardsResponse(BaseModel):
#     boards: List[BoardInfo]
#     count: int
#     error: Optional[str] = None
#     note: Optional[str] = None


# class ChecklistItem(BaseModel):
#     id: str
#     name: str
#     state: str  # "complete" or "incomplete"
#     checklist_id: str
#     checklist_name: str
#     card_id: str
#     card_name: str
#     list_id: str
#     list_name: str


# class ListInfo(BaseModel):
#     id: str
#     name: str
#     cards: List[Dict[str, Any]]
#     checklist_items: List[ChecklistItem]


# class CardInfo(BaseModel):
#     id: str
#     name: str
#     desc: Optional[str] = None
#     closed: bool = False
#     shortUrl: Optional[str] = None
#     url: Optional[str] = None
#     dateLastActivity: Optional[str] = None
#     due: Optional[str] = None
#     dueComplete: bool = False
#     list_id: str
#     list_name: str
#     comments_count: int = 0
#     badges: Optional[Dict[str, Any]] = None
#     labels: Optional[List[Dict[str, Any]]] = None
#     members: Optional[List[str]] = None
#     checklists_count: int = 0


# class CardsResponse(BaseModel):
#     cards: List[CardInfo]
#     count: int


# # llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=gemini_api_key)

# # def extract_participant_name(query: str) -> list[str]:
# #     """
# #     Extracts the participant name from the query using regex patterns.
# #     Returns a list with the name in format "{name}'s Todo".
# #     """
# #     patterns = [
# #         re.compile(r"(\w+)'s", re.IGNORECASE),
# #         re.compile(r"from\s+(\w+)\s+workspace", re.IGNORECASE),
# #         re.compile(r"from\s+(\w+)\s+Card", re.IGNORECASE),
# #         re.compile(r"from\s+(\w+)\s+bundle of work", re.IGNORECASE),
# #         re.compile(r"(\w+)\s+workspace", re.IGNORECASE),
# #         re.compile(r"(\w+)\s+Card", re.IGNORECASE),
# #     ]

# #     for pattern in patterns:
# #         match = pattern.search(query)
# #         if match:
# #             name = match.group(1)
# #             # Always return in format "{name}'s Todo"
# #             return [f"{name}'s Todo"]

# #     # If no specific participant name pattern is found, return empty list
# #     return []


# # async def get_user_name(query: str):
# #     """
# #     Get user name from query parameter using regex first, then LLM as fallback.
# #     """
# #     # Try regex extraction first (faster and more reliable)
# #     regex_result = extract_participant_name(query)
# #     if regex_result:
# #         return json.dumps(regex_result)
    
# #     # Fallback to LLM if regex doesn't work
# #     prompt = f"""Extract the participant name from this query and return ONLY a JSON list with the name in format "{{name}}'s Todo". Always use the apostrophe format. Do NOT include any code blocks, markdown, explanations, or other text. Just return the JSON list.

# # Query: {query}

# # Examples:
# # - "Fetch all tasks from Taran's Card" -> ["Taran's Todo"]
# # - "I wanna fetch all tasks from Garv workspace" -> ["Garv's Todo"]
# # - "Fetch tasks from Manreet's bundle of work" -> ["Manreet's Todo"]

# # IMPORTANT: Always return in format "{{name}}'s Todo" with the apostrophe. Return ONLY the JSON list, nothing else:"""

# #     try:
# #         user_name = llm.invoke(prompt)
# #         content = user_name.content.strip()
        
# #         # Remove markdown code blocks if present
# #         content = re.sub(r'```(?:json|python)?\s*\n?', '', content)
# #         content = re.sub(r'```\s*$', '', content)
# #         content = content.strip()
        
# #         return content
# #     except Exception as e:
# #         # If LLM fails, try regex one more time
# #         regex_result = extract_participant_name(query)
# #         if regex_result:
# #             return json.dumps(regex_result)
# #         raise HTTPException(
# #             status_code=500,
# #             detail=f"Failed to extract user name: {str(e)}"
# #         )


# # def _extract_id_from_result(res) -> Optional[str]:
# #     """Extract ID from Composio result"""
# #     if not res:
# #         return None
# #     if isinstance(res, dict):
# #         if "id" in res:
# #             return res["id"]
# #         for key in ("list", "card", "checklist", "data", "result"):
# #             v = res.get(key)
# #             if isinstance(v, dict) and "id" in v:
# #                 return v["id"]
# #     try:
# #         text = json.dumps(res) if not isinstance(res, str) else res
# #         m = re.search(r'"id"\s*:\s*"([0-9a-fA-F\-]+)"', text)
# #         if m:
# #             return m.group(1)
# #     except Exception:
# #         pass
# #     return None


# # def _parse_user_name(user_name_str: str) -> Optional[str]:

# #     if not user_name_str:
# #         return None
    
# #     # Remove markdown code blocks
# #     cleaned = re.sub(r'```(?:json|python)?\s*\n?', '', user_name_str)
# #     cleaned = re.sub(r'```\s*$', '', cleaned)
# #     cleaned = cleaned.strip()
    
# #     # Try to parse as JSON list first
# #     try:
# #         parsed = json.loads(cleaned)
# #         if isinstance(parsed, list) and len(parsed) > 0:
# #             name = parsed[0]
# #             if isinstance(name, str):
# #                 return name
# #     except (json.JSONDecodeError, TypeError):
# #         pass
    
# #     # Try to extract from string representation like ["Name Todo"] or ['Name Todo']
# #     # Look for the first quoted string
# #     match = re.search(r'["\']([^"\']+?)["\']', cleaned)
# #     if match:
# #         return match.group(1)
    
# #     # Try to extract from patterns like ["Garv Todo"] or [Garv Todo]
# #     match = re.search(r'\[["\']?([^"\']+?)["\']?\]', cleaned)
# #     if match:
# #         return match.group(1).strip()
    
# #     # If it's already a clean string, return it
# #     cleaned_str = cleaned.strip()
# #     if cleaned_str:
# #         return cleaned_str
    
# #     return None


# # def _is_card_like_list(lst: list) -> bool:
# #     """
# #     Heuristic: Determine whether a list looks like a Trello cards list.
# #     """
# #     if not isinstance(lst, list) or len(lst) == 0:
# #         return False
# #     # Look for dicts that have typical card keys
# #     sample = lst[0]
# #     if isinstance(sample, dict):
# #         keys = set(sample.keys())
# #         if "id" in keys and ("name" in keys or "idList" in keys or "shortUrl" in keys):
# #             return True
# #     return False


# # def _find_cards_recursive(obj: Any) -> Optional[list]:
# #     """
# #     Recursively search an object for a list that looks like Trello cards.
# #     """
# #     if isinstance(obj, list):
# #         if _is_card_like_list(obj):
# #             return obj
# #         # maybe list of lists/dicts - try children
# #         for item in obj:
# #             res = _find_cards_recursive(item)
# #             if res:
# #                 return res
# #         return None
# #     elif isinstance(obj, dict):
# #         # direct possible keys
# #         for key in ("cards", "data", "result", "items", "payload", "cardsList"):
# #             if key in obj and isinstance(obj[key], list) and _is_card_like_list(obj[key]):
# #                 return obj[key]
# #         # try any nested dict/list
# #         for v in obj.values():
# #             res = _find_cards_recursive(v)
# #             if res:
# #                 return res
# #     return None


# # def trello_get_boards_cards_by_id_board(api_key: str, idBoard: str) -> Dict[str, Any]:
# #     """
# #     Fetch all cards from a Trello board using TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD
# #     """
# #     toolset = ComposioToolSet(api_key=api_key)
# #     entity = toolset.get_entity()

# #     # Check Trello connection
# #     try:
# #         connection = entity.get_connection(app="trello")
# #         if connection.status != "ACTIVE":
# #             return {
# #                 "successful": False,
# #                 "data": {},
# #                 "error": "Trello is not connected. Please connect Trello first."
# #             }
# #     except NoItemsFound:
# #         return {
# #             "successful": False,
# #             "data": {},
# #             "error": "Trello is not connected. Please connect Trello first."
# #         }

# #     try:
# #         # ✅ ONLY valid param according to schema
# #         cards_result = toolset.execute_action(
# #             action="TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD",
# #             params={
# #                 "idBoard": idBoard
# #             },
# #             entity_id=entity.id
# #         )

# #         # Normalize Composio response
# #         if isinstance(cards_result, dict):
# #             is_successful = cards_result.get("successful", True)
# #             if "successfull" in cards_result:
# #                 is_successful = cards_result.get("successfull", True)

# #             if not is_successful:
# #                 return {
# #                     "successful": False,
# #                     "data": {},
# #                     "error": cards_result.get("error", "Unknown error")
# #                 }

# #             data = cards_result.get("data", cards_result)
# #             return {
# #                 "successful": True,
# #                 "data": data,
# #                 "error": None
# #             }

# #         if isinstance(cards_result, list):
# #             return {
# #                 "successful": True,
# #                 "data": cards_result,
# #                 "error": None
# #             }

# #         return {
# #             "successful": True,
# #             "data": cards_result,
# #             "error": None
# #         }

# #     except Exception as e:
# #         return {
# #             "successful": False,
# #             "data": {},
# #             "error": str(e)
# #         }


# # async def get_user_todo_card(query: str, composio_api_key: str, idBoard: str):
# #     """
# #     Fetch checklist items from a user's Todo card based on query.
    
# #     Args:
# #         query: User query containing the name to search for
# #         composio_api_key: Composio API key
# #         idBoard: Trello board ID
        
# #     Returns:
# #         Dictionary with card info and checklist items
# #     """
# #     user_name_raw = await get_user_name(query)
# #     if not user_name_raw:
# #         raise HTTPException(
# #             status_code=400,
# #             detail="User name not found. Please try again with a different query."
# #         )
    
# #     # Parse user name from LLM response
# #     user_name = _parse_user_name(user_name_raw)
# #     if not user_name:
# #         raise HTTPException(
# #             status_code=400,
# #             detail="Could not parse user name from query. Please try again with a different query."
# #         )
    
# #     # Get all cards from the board using TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD
# #     cards_response = trello_get_boards_cards_by_id_board(
# #         api_key=composio_api_key,
# #         idBoard=idBoard
# #     )
    
# #     # Check if request was successful
# #     if not cards_response.get("successful", False):
# #         error_msg = cards_response.get("error", "Unknown error")
# #         raise HTTPException(
# #             status_code=400,
# #             detail=f"Failed to fetch cards: {error_msg}"
# #         )
    
# #     # Extract cards from data
# #     data = cards_response.get("data", {})
    
# #     # Parse cards from data - data might be a list or dict with cards
# #     cards = []
# #     if isinstance(data, list):
# #         cards = data
# #     elif isinstance(data, dict):
# #         if "cards" in data and isinstance(data["cards"], list):
# #             cards = data["cards"]
# #         else:
# #             # Try to find a list of card-like objects anywhere in the dict
# #             found = _find_cards_recursive(data)
# #             if found:
# #                 cards = found
# #             else:
# #                 # last resort: consider dict values that are lists of dicts with id/name
# #                 for v in data.values():
# #                     if isinstance(v, list) and _is_card_like_list(v):
# #                         cards = v
# #                         break
    
# #     if not cards:
# #         raise HTTPException(
# #             status_code=404,
# #             detail="No cards found on the board."
# #         )
    
# #     # Find card matching user's Todo
# #     # Extract base name from "Name's Todo" or "Name Todo" format
# #     base_name = user_name.replace(" Todo", "").strip()
# #     # Remove trailing 's if present (e.g., "Garv's" -> "Garv")
# #     if base_name.endswith("'s"):
# #         base_name = base_name[:-2]
    
# #     # Try multiple patterns for matching (prioritize exact match first)
# #     patterns_to_try = [
# #         user_name,                # "Garv's Todo" (exact match - highest priority)
# #         f"{base_name}'s Todo",    # "Garv's Todo" (preferred format)
# #         f"{base_name} Todo",      # "Garv Todo" (fallback)
# #         f"{base_name}'s",         # "Garv's"
# #         base_name,                # "Garv"
# #     ]
    
# #     matched_card = None
# #     for card in cards:
# #         if not isinstance(card, dict):
# #             continue
# #         card_name = card.get("name", "").strip()
# #         card_name_lower = card_name.lower()
        
# #         # Try exact match first (case-sensitive)
# #         if card_name in patterns_to_try:
# #             matched_card = card
# #             break
        
# #         # Try case-insensitive match
# #         for pattern in patterns_to_try:
# #             if card_name_lower == pattern.lower():
# #                 matched_card = card
# #                 break
        
# #         if matched_card:
# #             break
        
# #         # Try if card name contains the base name (fuzzy match)
# #         if base_name.lower() in card_name_lower or card_name_lower in base_name.lower():
# #             if any(keyword in card_name_lower for keyword in ["todo", "task", base_name.lower()]):
# #                 matched_card = card
# #                 break
    
# #     if not matched_card:
# #         # List available card names for debugging
# #         available_cards = [card.get("name", "Unnamed") for card in cards if isinstance(card, dict)]
# #         raise HTTPException(
# #             status_code=404,
# #             detail=f"Card matching '{user_name}' (base: '{base_name}') not found. Available cards: {available_cards[:10]}"  # Show first 10 cards
# #         )
    
# #     card_id = _extract_id_from_result(matched_card)
# #     if not card_id:
# #         raise HTTPException(
# #             status_code=500,
# #             detail="Could not extract card ID from matched card."
# #         )
    
# #     # Get checklists on the card
# #     toolset = ComposioToolSet(api_key=composio_api_key)
# #     entity = toolset.get_entity()
# #     checklists_result = toolset.execute_action(
# #         action="TRELLO_GET_CARDS_CHECKLISTS_BY_ID_CARD",
# #         params={"idCard": card_id},
# #         entity_id=entity.id
# #     )
    
# #     if not checklists_result:
# #         return {
# #             "card_id": card_id,
# #             "card_name": matched_card.get("name", ""),
# #             "checklists": [],
# #             "checklist_items": []
# #         }
    
# #     # Parse checklists
# #     checklists = []
# #     if isinstance(checklists_result, list):
# #         checklists = checklists_result
# #     elif isinstance(checklists_result, dict):
# #         if "checklists" in checklists_result and isinstance(checklists_result["checklists"], list):
# #             checklists = checklists_result["checklists"]
# #         elif "id" in checklists_result:
# #             checklists = [checklists_result]
# #         else:
# #             found = _find_cards_recursive(checklists_result)
# #             if found:
# #                 checklists = found
    
# #     all_checklist_items = []
# #     checklists_info = []
    
# #     # Get items from each checklist
# #     for checklist in checklists:
# #         if not isinstance(checklist, dict):
# #             continue
            
# #         checklist_id = _extract_id_from_result(checklist)
# #         if not checklist_id:
# #             continue
        
# #         checklist_name = checklist.get("name", "Unnamed Checklist")
# #         checklists_info.append({
# #             "id": checklist_id,
# #             "name": checklist_name
# #         })
        
# #         # Get checklist items
# #         items_result = toolset.execute_action(
# #             action="TRELLO_GET_CARDS_CHECKLIST_CHECK_ITEMS_BY_ID_CARD_BY_ID_CHECKLIST",
# #             params={"idCard": card_id, "idChecklist": checklist_id},
# #             entity_id=entity.id
# #         )
        
# #         if not items_result:
# #             continue
        
# #         # Parse items
# #         items = []
# #         if isinstance(items_result, list):
# #             items = items_result
# #         elif isinstance(items_result, dict):
# #             if "checkItems" in items_result and isinstance(items_result["checkItems"], list):
# #                 items = items_result["checkItems"]
# #             elif "id" in items_result:
# #                 items = [items_result]
# #             else:
# #                 found = _find_cards_recursive(items_result)
# #                 if found:
# #                     items = found
        
# #         # Format checklist items
# #         for item in items:
# #             if isinstance(item, dict):
# #                 all_checklist_items.append({
# #                     "id": item.get("id", ""),
# #                     "name": item.get("name", ""),
# #                     "state": item.get("state", "incomplete"),  # "complete" or "incomplete"
# #                     "checklist_id": checklist_id,
# #                     "checklist_name": checklist_name,
# #                     "card_id": card_id,
# #                     "card_name": matched_card.get("name", "")
# #                 })
    
# #     return {
# #         "card_id": card_id,
# #         "card_name": matched_card.get("name", ""),
# #         "card_desc": matched_card.get("desc", ""),
# #         "checklists": checklists_info,
# #         "checklist_items": all_checklist_items,
# #         "total_items": len(all_checklist_items)
# #     }


# # async def main():
# #     # First, let's check the action schema to see what parameters it expects
# #     toolset = ComposioToolSet(api_key=composio_api_key)
# #     try:
# #         # Get action schema
# #         action_schemas = toolset.get_action_schemas(actions=[Action.TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD])
# #         if action_schemas:
# #             schema = action_schemas[0]
# #             print("Action Schema:")
# #             print(f"Name: {schema.name}")
# #             try:
# #                 params_prop = schema.parameters.properties if hasattr(schema.parameters, 'properties') else schema.parameters
# #                 print(f"Parameters: {json.dumps(params_prop, indent=2)}")
# #             except Exception:
# #                 # If parameters serialization fails, ignore gracefully
# #                 pass
# #             if hasattr(schema.parameters, 'required'):
# #                 print(f"Required: {schema.parameters.required}")
# #     except Exception as e:
# #         print(f"Could not get action schema: {str(e)}")
    
# #     query = "I wanna fetch all the tasks and descriptions from Garv workspace"
    
# #     # Extract and parse user name
# #     user_name_raw = await get_user_name(query)
# #     parsed_name = _parse_user_name(user_name_raw)
# #     print(f"Extracted user name (raw): {user_name_raw}")
# #     print(f"Parsed user name: {parsed_name}")
    
# #     # TODO: Replace with actual board ID
# #     board_id = "68e165740b9127730f614a5d" 
# #     if board_id == "YOUR_BOARD_ID_HERE":
# #         print("Warning: Please set board_id before running")
# #         return
    
# #     try:
# #         card_info = await get_user_todo_card(query, composio_api_key, board_id)
# #         print(f"Card info: {json.dumps(card_info, indent=2)}")
# #     except HTTPException as e:
# #         print(f"Error: {e.status_code} - {e.detail}")
# #     except Exception as e:
# #         print(f"Unexpected error: {str(e)}")
# #         import traceback
# #         traceback.print_exc()


# # # LIST BOARDS (use this first)
# # toolset = ComposioToolSet(api_key=composio_api_key)
# # entity = toolset.get_entity()
# # try:
# #     conn = entity.get_connection(app="trello")
# #     print("Using connection id:", getattr(conn, "id", None))
# #     print("Using connection accountId:", getattr(conn, "accountId", None))

# #     # NOTE: use idMember (required by the schema)
# #     result = toolset.execute_action(
# #         action="TRELLO_GET_MEMBERS_BOARDS_BY_ID_MEMBER",
# #         params={"idMember": "me"},
# #         entity_id=entity.id
# #     )

# #     import json
# #     print("TYPE:", type(result))
# #     if isinstance(result, dict):
# #         print("Top-level keys:", list(result.keys()))
# #     # pretty print truncated
# #     try:
# #         text = json.dumps(result, default=str, indent=2)
# #     except Exception:
# #         text = str(result)
# #     print("\n--- BEGIN TRUNCATED RESULT (first 4000 chars) ---")
# #     print(text[:4000])
# #     print("--- END TRUNCATED RESULT ---\n")

# #     # Try to extract boards list robustly
# #     boards = []
# #     if isinstance(result, dict):
# #         for key in ("data", "boards", "result", "items"):
# #             if key in result and isinstance(result[key], list):
# #                 boards = result[key]
# #                 break
# #         # fallback: collect any top-level list of dicts with id/name
# #         if not boards:
# #             for v in result.values():
# #                 if isinstance(v, list) and len(v) > 0 and isinstance(v[0], dict) and v[0].get("id") and v[0].get("name"):
# #                     boards = v
# #                     break
# #     elif isinstance(result, list):
# #         boards = result

# #     print(f"Found {len(boards)} boards")
# #     for i, b in enumerate(boards[:50], 1):
# #         print(f"{i}. id: {b.get('id')}, name: {b.get('name')}, url: {b.get('url')}")
# # except Exception as e:
# #     import traceback
# #     traceback.print_exc()







# # if __name__ == "__main__":
# #     asyncio.run(main())



# @router.post("/trello/initiate", response_model=InitiateConnectionResponse)
# async def initiate_trello_auth(
#     redirect_url: Optional[str] = Query(None),
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Initiate Trello OAuth connection via Composio
#     Returns a redirect URL that the user needs to visit to authorize Trello
#     """
#     # Get user settings
#     user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
    
#     settings = user.get("settings", {})
#     if not isinstance(settings, dict):
#         settings = {}
    
#     composio_api_key = settings.get("composio_api_key", "")
#     if composio_api_key:
#         composio_api_key = composio_api_key.strip()
    
#     if not composio_api_key:
#         raise HTTPException(
#             status_code=400,
#             detail="Composio API key not configured. Please add it in Settings first."
#         )
    
#     try:
#         result = initiate_trello_connection(
#             api_key=composio_api_key,
#             redirect_url=redirect_url
#         )
        
#         # Store connection request ID in user settings (optional, for tracking)
#         # await database.users.update_one(
#         #     {"_id": ObjectId(current_user["id"])},
#         #     {"$set": {"settings.composio_connection_id": result["connected_account_id"]}}
#         # )
        
#         return InitiateConnectionResponse(
#             redirect_url=result["redirect_url"],
#             connected_account_id=result["connected_account_id"],
#             connection_status=result["connection_status"]
#         )
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to initiate Trello connection: {str(e)}"
#         )


# @router.post("/trello/disconnect")
# async def disconnect_trello_endpoint(
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Disconnect Trello connection - allows user to reconnect with proper permissions
#     """

#     user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
#     composio_api_key = user.get("settings", {}).get("composio_api_key", "").strip()
    
#     if not composio_api_key:
#         raise HTTPException(
#             status_code=400,
#             detail="Composio API key not configured. Please add it in Settings first."
#         )
    
#     try:
#         result = disconnect_trello(api_key=composio_api_key)
#         return result
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to disconnect Trello: {str(e)}"
#         )


# @router.get("/trello/status", response_model=ConnectionStatusResponse)
# async def get_trello_connection_status(
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Check if Trello is connected via Composio
#     """
#     # Get user settings
#     user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
    
#     settings = user.get("settings", {})
#     if not isinstance(settings, dict):
#         settings = {}
    
#     composio_api_key = settings.get("composio_api_key", "")
#     if composio_api_key:
#         composio_api_key = composio_api_key.strip()
    
#     if not composio_api_key:
#         raise HTTPException(
#             status_code=400,
#             detail="Composio API key not configured. Please add it in Settings first."
#         )
    
#     try:
#         result = check_trello_connection(api_key=composio_api_key)
#         return ConnectionStatusResponse(**result)
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to check Trello connection: {str(e)}"
#         )


# @router.get("/trello/boards", response_model=BoardsResponse)
# async def get_trello_boards_endpoint(
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Fetch all Trello boards for the authenticated user
#     """
#     user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
#     composio_api_key = user.get("settings", {}).get("composio_api_key", "").strip()
    
#     if not composio_api_key:
#         raise HTTPException(
#             status_code=400,
#             detail="Composio API key not configured. Please add it in Settings first."
#         )
    
#     try:
#         result = get_trello_boards(api_key=composio_api_key)
#         return BoardsResponse(**result)
#     except Exception as e:
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to fetch Trello boards: {str(e)}"
#         )




# @router.get("/trello/cards", response_model=CardsResponse)
# async def get_trello_cards_endpoint(
#     board_id: str = Query(..., description="Trello board ID"),
#     current_user: dict = Depends(get_current_user)
# ):
#     """
#     Fetch all cards from a Trello board with full details
#     """
#     # Get user settings
#     user = await database.users.find_one({"_id": ObjectId(current_user["id"])})
#     if not user:
#         raise HTTPException(status_code=404, detail="User not found")
    
#     settings = user.get("settings", {})
#     if not isinstance(settings, dict):
#         settings = {}
    
#     composio_api_key = settings.get("composio_api_key", "")
#     if composio_api_key:
#         composio_api_key = composio_api_key.strip()
    
#     if not composio_api_key:
#         raise HTTPException(
#             status_code=400,
#             detail="Composio API key not configured. Please add it in Settings first."
#         )
    
#     # Get board_id from settings if not provided
#     workspace_id = user.get("settings", {}).get("workspace_id")
#     if not board_id and workspace_id:
#         board_id = workspace_id
    
#     if not board_id:
#         raise HTTPException(
#             status_code=400,
#             detail="Board ID is required. Please provide board_id parameter or configure it in Settings."
#         )
    
#     try:
#         result = get_trello_cards(api_key=composio_api_key, board_id=board_id)
#         print(f"DEBUG: get_trello_cards returned {result.get('count', 0)} cards")
#         return CardsResponse(**result)
#     except Exception as e:
#         import traceback
#         print(f"ERROR in get_trello_cards_endpoint: {str(e)}")
#         traceback.print_exc()
#         raise HTTPException(
#             status_code=500,
#             detail=f"Failed to fetch Trello cards: {str(e)}"
#         )

