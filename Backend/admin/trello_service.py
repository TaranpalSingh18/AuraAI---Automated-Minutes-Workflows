"""
AdminPerspective Trello service - Assign tasks to employees using Trello REST API

Features:
- Uses TRELLO_API_KEY / TRELLO_API_TOKEN from env
- Create / find lists and cards
- Create checklists and checklist items (tasks)
- Optional Gemini LLM parsing if GEMINI_API_KEY set (uses langchain_google_genai ChatGoogleGenerativeAI)
- Production-minded: timeouts, error messages, simple fallback parsing when LLM not available
"""

from __future__ import annotations
import os
import requests
import logging
import json
import re
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

TRELLO_BASE = "https://api.trello.com/1"
TRELLO_KEY = os.getenv("TRELLO_API_KEY")
TRELLO_TOKEN = os.getenv("TRELLO_API_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# optional LLM
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:
    ChatGoogleGenerativeAI = None


def _safe_json(obj) -> str:
    try:
        return json.dumps(obj, ensure_ascii=False)
    except Exception:
        return str(obj)


class AdminTrelloService:
    """
    Admin Trello service for creating/assigning tasks on a board.
    Default behavior: create list "{User}'s Todo" and create a card with task_text inside it.
    """

    def __init__(self, board_id: Optional[str] = None, gemini_api_key: Optional[str] = None):
        if not TRELLO_KEY or not TRELLO_TOKEN:
            raise RuntimeError("TRELLO_API_KEY and TRELLO_API_TOKEN must be set in environment variables")

        self.key = TRELLO_KEY
        self.token = TRELLO_TOKEN
        self.board_id = board_id
        self.timeout = 15

        gemini_key = gemini_api_key or GEMINI_API_KEY
        if gemini_key and ChatGoogleGenerativeAI is not None:
            try:
                self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=gemini_key)
            except Exception as e:
                logger.warning("Could not init LLM: %s", e)
                self.llm = None
        else:
            self.llm = None

    # ---------------- HTTP helper ----------------
    def _request(self, method: str, path: str, params: Optional[dict] = None, json_body: Optional[dict] = None):
        params = params.copy() if params else {}
        params.update({"key": self.key, "token": self.token})

        url = f"{TRELLO_BASE}{path}"
        logger.debug("Trello %s %s params=%s json=%s", method, url, params, _safe_json(json_body))
        resp = requests.request(method, url, params=params, json=json_body, timeout=self.timeout)
        if resp.status_code >= 400:
            logger.error("Trello API error %s %s -> %s", resp.status_code, resp.text, url)
            raise RuntimeError(f"Trello API error {resp.status_code}: {resp.text}")
        try:
            return resp.json()
        except ValueError:
            return resp.text

    # ---------------- Board / List / Card ----------------
    def get_board_lists(self) -> List[Dict[str, Any]]:
        """Return lists on the board"""
        if not self.board_id:
            raise ValueError("board_id not set")
        return self._request("GET", f"/boards/{self.board_id}/lists", {"cards": "none", "fields": "name,closed"})

    def ensure_list_exists(self, list_name: str) -> str:
        """
        Return list id for list_name. Create if missing.
        Case-insensitive match.
        """
        if not self.board_id:
            raise ValueError("board_id not set")

        lists = self.get_board_lists()
        target = list_name.strip().lower()
        for lst in lists:
            if lst.get("name", "").strip().lower() == target and not lst.get("closed", False):
                logger.info("Found existing list '%s' -> %s", list_name, lst.get("id"))
                return lst["id"]

        # create list (POST /lists with idBoard)
        res = self._request("POST", f"/lists", {"idBoard": self.board_id, "name": list_name})
        list_id = res.get("id")
        logger.info("Created list '%s' -> %s", list_name, list_id)
        return list_id

    def get_list_cards(self, list_id: str) -> List[Dict[str, Any]]:
        return self._request("GET", f"/lists/{list_id}/cards", {"fields": "id,name,closed,desc"})

    def find_card_by_name_on_board(self, card_name: str) -> Optional[Dict[str, Any]]:
        """
        Search all board cards for exact or prefix name match. Returns card dict or None.
        """
        if not self.board_id:
            raise ValueError("board_id not set")
        cards = self._request("GET", f"/boards/{self.board_id}/cards", {"fields": "id,name,idList,closed"})
        for c in cards:
            if c.get("closed", False):
                continue
            name = c.get("name", "")
            if name.strip().lower() == card_name.strip().lower() or name.strip().lower().startswith(card_name.strip().lower()):
                return c
        return None

    def create_card(self, list_id: str, name: str, desc: Optional[str] = None) -> Dict[str, Any]:
        """Create a card in list_id"""
        params = {"idList": list_id, "name": name}
        if desc is not None:
            params["desc"] = desc
        card = self._request("POST", "/cards", params)
        logger.info("Created card '%s' -> %s", name, card.get("id"))
        return card

    # ---------------- Checklists / Items ----------------
    def get_card_checklists(self, card_id: str) -> List[Dict[str, Any]]:
        return self._request("GET", f"/cards/{card_id}/checklists", {"fields": "name"})

    def ensure_checklist(self, card_id: str, checklist_name: str) -> str:
        """
        Return checklist id for card_id + checklist_name. Create if missing.
        """
        checklists = self.get_card_checklists(card_id)
        for cl in checklists:
            if cl.get("name", "").strip().lower() == checklist_name.strip().lower():
                return cl["id"]

        # create checklist via POST /checklists
        res = self._request("POST", "/checklists", {"idCard": card_id, "name": checklist_name})
        return res.get("id")

    def add_checklist_item(self, checklist_id: str, item_name: str) -> Dict[str, Any]:
        res = self._request("POST", f"/checklists/{checklist_id}/checkItems", {"name": item_name})
        logger.info("Added checklist item to %s", checklist_id)
        return res

    # ---------------- High-level Admin flows ----------------
    def assign_task_to_user(
        self,
        user_name: str,
        task_text: str,
        board_list_name: Optional[str] = None,
        create_list_if_missing: bool = True,
        create_card_per_task: bool = True,
        add_to_checklist: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        High-level helper for admin:
        - if board_list_name provided, use it; else default to "{user_name}'s Todo"
        - ensures list exists (optionally creates)
        - creates a card for the task (default) or adds a checklist item to a user's card
        - returns helpful metadata
        Params:
          user_name: "Vatsal" or "Vatsal Shah"
          task_text: what to create
          board_list_name: optional explicit list name to use
          create_card_per_task: if True create a new card named task_text inside the list
          add_to_checklist: if provided, create/get checklist of that name on the created/found card and add item
        """
        if not self.board_id:
            raise ValueError("board_id not set")

        # by default use "<User>'s Todo" as list name
        list_name = board_list_name or f"{user_name}'s Todo"

        if create_list_if_missing:
            list_id = self.ensure_list_exists(list_name)
        else:
            lists = self.get_board_lists()
            list_id = next((l["id"] for l in lists if l.get("name", "").strip().lower() == list_name.strip().lower()), None)
            if not list_id:
                raise RuntimeError(f"List '{list_name}' not found and creation disabled")

        # create a card for this task inside the user's list
        if create_card_per_task:
            card = self.create_card(list_id, task_text, desc=f"Assigned to {user_name}")
            card_id = card.get("id")
            result = {"success": True, "list_id": list_id, "card_id": card_id, "message": f"Created card in list '{list_name}'"}
            # optionally add checklist item to the newly created card
            if add_to_checklist:
                checklist_id = self.ensure_checklist(card_id, add_to_checklist)
                self.add_checklist_item(checklist_id, task_text)
                result.update({"checklist_id": checklist_id})
            return result

        # alternative flow: find or create user's card inside the list and append checklist item
        # user_card_name = f"{user_name}'s Todo"
        cards = self.get_list_cards(list_id)
        user_card = None
        target_card_name = f"{user_name}'s Todo"
        for c in cards:
            name = c.get("name", "")
            if name.strip().lower() == target_card_name.strip().lower() or name.strip().lower().startswith(user_name.strip().lower()):
                user_card = c
                break
        if not user_card:
            user_card = self.create_card(list_id, target_card_name, desc=f"Auto-created Todo card for {user_name}")

        card_id = user_card.get("id")
        checklist_name = add_to_checklist or "Tasks"
        checklist_id = self.ensure_checklist(card_id, checklist_name)
        self.add_checklist_item(checklist_id, task_text)

        return {
            "success": True,
            "list_id": list_id,
            "card_id": card_id,
            "checklist_id": checklist_id,
            "message": f"Added checklist item to card in list '{list_name}'"
        }

    # ---------------- Natural language parsing ----------------
    def _llm_parse_assignment(self, query: str, available_users: List[str]) -> Dict[str, str]:
        """
        Use Gemini LLM (if configured) to parse employee name and task_description.
        Returns {'employee_name': str, 'task_description': str}
        """
        if not self.llm:
            return {"employee_name": "", "task_description": ""}

        users_text = ", ".join(available_users)
        prompt = (
            f"You are a task assignment assistant. Extract employee name and the task to assign.\n"
            f"Available team members: {users_text}\n"
            f"User query: {query}\n\n"
            f"Respond with JSON only: {{\"employee_name\":\"\", \"task_description\":\"\"}}"
        )
        try:
            resp = self.llm.invoke(prompt)
            text = getattr(resp, "content", str(resp)) or ""
            cleaned = re.sub(r'^```json\s*', '', text.strip())
            cleaned = re.sub(r'```\s*$', '', cleaned.strip())
            parsed = json.loads(cleaned)
            return {
                "employee_name": parsed.get("employee_name", "").strip(),
                "task_description": parsed.get("task_description", "").strip()
            }
        except Exception as e:
            logger.warning("LLM parse failed: %s", e)
            return {"employee_name": "", "task_description": ""}

    def parse_task_assignment(self, query: str, available_users: List[str]) -> Dict[str, Any]:
        """
        Public parser: tries LLM first (if available), then falls back to heuristics:
        - find user whose name appears in query (case-insensitive)
        - remaining text as task description
        Returns {employee_name, task_description}
        """
        result = {"employee_name": "", "task_description": ""}

        if self.llm:
            result = self._llm_parse_assignment(query, available_users)
            if result.get("employee_name") and result.get("task_description"):
                return result

        q_lower = query.lower()
        for user in available_users:
            if user.lower() in q_lower:
                result["employee_name"] = user
                desc = re.sub(re.escape(user), "", query, flags=re.IGNORECASE).strip(" -,:;")
                # try to remove words like 'assign' 'to' 'task' if present at start
                desc = re.sub(r'^(assign|add|create|please)\b', '', desc, flags=re.IGNORECASE).strip()
                result["task_description"] = desc or ""
                return result

        # split by quotes to extract an explicit quoted task
        m = re.search(r'"([^"]+)"', query)
        if m:
            result["task_description"] = m.group(1).strip()
            # try to find name after "to"
            m2 = re.search(r'to\s+([A-Za-z ]+)$', query, flags=re.IGNORECASE)
            if m2:
                result["employee_name"] = m2.group(1).strip()
            return result

        # fallback simple heuristics
        if " to " in q_lower:
            parts = re.split(r"\bto\b", query, maxsplit=1, flags=re.IGNORECASE)
            result["task_description"] = parts[0].strip()
            result["employee_name"] = parts[-1].strip()
            return result

        result["task_description"] = query.strip()
        return result


# ---------- Database hook (if main needs to set DB) ----------
database = None


def set_database(db):
    global database
    database = db






# iske niche uncomment karo 
# """
# AdminPerspective Trello service - Assign tasks to employees using Composio
# """
# import sys
# import os
# from pathlib import Path
# from typing import List, Dict, Any, Optional
# from langchain_google_genai import ChatGoogleGenerativeAI
# import json
# import re

# # Add Composio path
# backend_dir = Path(__file__).parent.parent
# composio_path = backend_dir.parent / "Model" / "composio" / "python"
# sys.path.insert(0, str(composio_path))

# try:
#     from plugins.langchain.composio_langchain.toolset import ComposioToolSet
# except ImportError:
#     try:
#         from composio.tools.toolset import ComposioToolSet
#     except ImportError:
#         ComposioToolSet = None


# class AdminTrelloService:
#     """Service for assigning tasks to employees via Trello"""
    
#     def __init__(self, composio_api_key: str, gemini_api_key: str):
#         if not composio_api_key:
#             raise ValueError("Composio API key is required")
#         if not gemini_api_key:
#             raise ValueError("Gemini API key is required")
        
#         if ComposioToolSet is None:
#             raise RuntimeError("ComposioToolSet not available. Please install Composio SDK.")
        
#         self.sdk = ComposioToolSet(api_key=composio_api_key)
#         self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=gemini_api_key)
    
#     def _safe_execute(self, action_name: str, params: dict) -> Optional[object]:
#         """Safely execute Composio action"""
#         try:
#             return self.sdk.execute_action(action=action_name, params=params)
#         except Exception as e:
#             print(f"Error executing {action_name}: {e}")
#             return None
    
#     def _extract_id_from_result(self, res) -> Optional[str]:
#         """Extract ID from Composio result"""
#         if not res:
#             return None
#         if isinstance(res, dict):
#             if "id" in res:
#                 return res["id"]
#             for key in ("list", "card", "checklist", "data", "result"):
#                 v = res.get(key)
#                 if isinstance(v, dict) and "id" in v:
#                     return v["id"]
#         try:
#             text = json.dumps(res) if not isinstance(res, str) else res
#             m = re.search(r'"id"\s*:\s*"([0-9a-fA-F\-]+)"', text)
#             if m:
#                 return m.group(1)
#         except Exception:
#             pass
#         return None
    
#     def ensure_list_exists(self, board_id: str, list_name: str) -> Optional[str]:
#         """Create or get list on board"""
#         action = "TRELLO_ADD_BOARDS_LISTS_BY_ID_BOARD"
#         params = {"idBoard": board_id, "name": list_name}
        
#         res = self._safe_execute(action, params)
#         list_id = self._extract_id_from_result(res)
#         return list_id
    
#     def get_or_create_user_card(self, board_id: str, list_id: str, user_name: str) -> Optional[str]:
#         """Get or create user's Todo card"""
#         card_name = f"{user_name}'s Todo"
        
#         # First, try to find existing card
#         action = "TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD"
#         params = {"idBoard": board_id}
        
#         cards_result = self._safe_execute(action, params)
#         if cards_result:
#             cards = []
#             if isinstance(cards_result, list):
#                 cards = cards_result
#             elif isinstance(cards_result, dict):
#                 if "cards" in cards_result:
#                     cards = cards_result["cards"]
#                 elif "id" in cards_result:
#                     cards = [cards_result]
            
#             for card in cards:
#                 if isinstance(card, dict):
#                     card_name_found = card.get("name", "")
#                     if card_name_found == card_name or card_name_found.startswith(f"{user_name}'"):
#                         card_id = self._extract_id_from_result(card)
#                         if card_id:
#                             return card_id
        
#         # Create new card
#         action = "TRELLO_ADD_CARDS"
#         params = {"idList": list_id, "name": card_name}
        
#         res = self._safe_execute(action, params)
#         card_id = self._extract_id_from_result(res)
#         return card_id
    
#     def add_task_to_card(self, card_id: str, checklist_name: str, task_text: str) -> bool:
#         """Add a task to card's checklist"""
#         # First, get or create checklist
#         checklist_id = None
        
#         # Get existing checklists
#         action = "TRELLO_GET_CARDS_CHECKLISTS_BY_ID_CARD"
#         params = {"idCard": card_id}
        
#         checklists_result = self._safe_execute(action, params)
#         if checklists_result:
#             checklists = []
#             if isinstance(checklists_result, list):
#                 checklists = checklists_result
#             elif isinstance(checklists_result, dict):
#                 if "checklists" in checklists_result:
#                     checklists = checklists_result["checklists"]
#                 elif "id" in checklists_result:
#                     checklists = [checklists_result]
            
#             for checklist in checklists:
#                 if isinstance(checklist, dict):
#                     if checklist.get("name") == checklist_name:
#                         checklist_id = self._extract_id_from_result(checklist)
#                         break
        
#         # Create checklist if doesn't exist
#         if not checklist_id:
#             action = "TRELLO_ADD_CARDS_CHECKLISTS_BY_ID_CARD"
#             params = {"idCard": card_id, "name": checklist_name}
            
#             res = self._safe_execute(action, params)
#             checklist_id = self._extract_id_from_result(res)
        
#         if not checklist_id:
#             return False
        
#         # Add task item to checklist
#         action = "TRELLO_ADD_CARDS_CHECKLIST_CHECK_ITEM_BY_ID_CARD_BY_ID_CHECKLIST"
#         params = {
#             "idCard": card_id,
#             "idChecklist": checklist_id,
#             "name": task_text
#         }
        
#         res = self._safe_execute(action, params)
#         return res is not None
    
#     def parse_task_assignment(self, query: str, available_users: List[str]) -> Dict[str, Any]:
#         """
#         Parse natural language query to extract: employee_name, task_description
#         Returns: {employee_name: str, task_description: str}
#         """
#         users_text = ", ".join(available_users)
        
#         prompt = f"""You are a task assignment assistant. Parse the user's query to extract:
# 1. The employee/team member's name
# 2. The task description to assign

# Available team members: {users_text}

# User query: {query}

# Respond with ONLY a JSON object with two keys:
# - "employee_name": the name of the employee (must match one from the list or be very similar)
# - "task_description": the task to assign

# Example response:
# {{"employee_name": "John", "task_description": "Complete the backend API documentation"}}

# If you cannot determine the employee name or task, use empty strings.

# Respond with JSON only, no other text:"""
        
#         response = self.llm.invoke(prompt)
#         response_text = response.content if hasattr(response, 'content') else str(response)
        
#         try:
#             cleaned = re.sub(r'^```json\s*', '', response_text.strip())
#             cleaned = re.sub(r'```\s*$', '', cleaned.strip())
#             parsed = json.loads(cleaned)
            
#             employee_name = parsed.get("employee_name", "").strip()
#             task_description = parsed.get("task_description", "").strip()
            
#             # Try to match employee name to available users (fuzzy match)
#             matched_name = None
#             for user in available_users:
#                 if user.lower() == employee_name.lower() or employee_name.lower() in user.lower():
#                     matched_name = user
#                     break
            
#             return {
#                 "employee_name": matched_name or employee_name,
#                 "task_description": task_description
#             }
#         except (json.JSONDecodeError, KeyError) as e:
#             print(f"Error parsing LLM response: {e}")
#             return {
#                 "employee_name": "",
#                 "task_description": ""
#             }


# # Database will be set from main.py
# database = None

# def set_database(db):
#     global database
#     database = db

