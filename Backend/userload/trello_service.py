import os
import requests
from typing import List, Dict, Optional

# --- Database hook (set from main) ---
database = None

def set_database(db):
    global database
    database = db


class UserLoadTrelloService:
    """
    Direct Trello API service (NO composio)
    Render-safe, production-ready
    """

    def __init__(self, board_id: str):
        self.trello_key = os.getenv("TRELLO_API_KEY")
        self.trello_token = os.getenv("TRELLO_API_TOKEN")

        if not self.trello_key or not self.trello_token:
            raise RuntimeError(
                "TRELLO_API_KEY and TRELLO_API_TOKEN must be set in environment variables"
            )

        if not board_id:
            raise ValueError("Trello board_id is required")

        self.board_id = board_id
        self.base_url = "https://api.trello.com/1"

    # ---------- INTERNAL HELPERS ----------

    def _request(
        self,
        method: str,
        path: str,
        params: Optional[dict] = None
    ):
        params = params or {}
        params.update({
            "key": self.trello_key,
            "token": self.trello_token
        })

        url = f"{self.base_url}{path}"

        res = requests.request(
            method=method,
            url=url,
            params=params,
            timeout=15
        )

        if res.status_code >= 400:
            raise RuntimeError(
                f"Trello API error {res.status_code}: {res.text}"
            )

        return res.json()

    # ---------- CORE API METHODS ----------

    def get_board_cards(self) -> List[Dict]:
        """
        Get all cards on the board
        """
        return self._request(
            "GET",
            f"/boards/{self.board_id}/cards",
            {
                "fields": "id,name,idList,closed",
                "checklists": "all"
            }
        )

    def get_user_tasks(
        self,
        user_name: str
    ) -> List[Dict]:
        """
        Find checklist items from card named "{user}'s Todo"
        """
        cards = self.get_board_cards()

        todo_card_name = f"{user_name}'s Todo"

        target_card = next(
            (
                c for c in cards
                if c.get("name") == todo_card_name and not c.get("closed", False)
            ),
            None
        )

        if not target_card:
            return []

        tasks = []
        for checklist in target_card.get("checklists", []):
            checklist_id = checklist.get("id")
            for item in checklist.get("checkItems", []):
                tasks.append({
                    "id": item.get("id"),
                    "name": item.get("name"),
                    "state": item.get("state"),
                    "checklist_id": checklist_id
                })

        return tasks

    def update_task_status(
        self,
        card_id: str,
        checklist_id: str,
        checkitem_id: str,
        completed: bool
    ) -> bool:
        """
        Mark checklist item complete/incomplete
        """
        state = "complete" if completed else "incomplete"

        self._request(
            "PUT",
            f"/cards/{card_id}/checklist/{checklist_id}/checkItem/{checkitem_id}",
            {"state": state}
        )

        return True









# iske niche uncomment karo 
# """
# UserLoad Trello service - fetch and manage user tasks from Trello via Composio
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


# class UserLoadTrelloService:
#     """Service for fetching and managing user tasks from Trello"""
    
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
    
#     def get_user_todo_card_id(self, workspace_id: str, board_id: str, user_name: str) -> Optional[str]:
#         """
#         Find the user's Todo card in the workspace/board
#         Card name should be "{user_name}'s Todo"
#         """
#         # Get all cards on the board
#         action = "TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD"
#         params = {"idBoard": board_id}
        
#         cards_result = self._safe_execute(action, params)
#         if not cards_result:
#             return None
        
#         # Parse cards - result might be list or dict
#         cards = []
#         if isinstance(cards_result, list):
#             cards = cards_result
#         elif isinstance(cards_result, dict):
#             if "cards" in cards_result:
#                 cards = cards_result["cards"]
#             elif "id" in cards_result:  # Single card
#                 cards = [cards_result]
        
#         # Find card matching user's Todo
#         card_name_pattern = f"{user_name}'s Todo"
#         for card in cards:
#             card_name = card.get("name", "") if isinstance(card, dict) else str(card)
#             if card_name == card_name_pattern or card_name.startswith(f"{user_name}'"):
#                 card_id = self._extract_id_from_result(card) if isinstance(card, dict) else None
#                 if card_id:
#                     return card_id
        
#         return None
    
#     def get_user_tasks(self, workspace_id: str, board_id: str, user_name: str) -> List[Dict[str, Any]]:
#         """
#         Fetch all tasks (checklist items) from user's Todo card
#         Returns list of tasks with: id, name, state (complete/incomplete)
#         """
#         card_id = self.get_user_todo_card_id(workspace_id, board_id, user_name)
#         if not card_id:
#             return []
        
#         # Get checklists on the card
#         action = "TRELLO_GET_CARDS_CHECKLISTS_BY_ID_CARD"
#         params = {"idCard": card_id}
        
#         checklists_result = self._safe_execute(action, params)
#         if not checklists_result:
#             return []
        
#         # Parse checklists
#         checklists = []
#         if isinstance(checklists_result, list):
#             checklists = checklists_result
#         elif isinstance(checklists_result, dict):
#             if "checklists" in checklists_result:
#                 checklists = checklists_result["checklists"]
#             elif "id" in checklists_result:
#                 checklists = [checklists_result]
        
#         all_tasks = []
        
#         # Get items from each checklist
#         for checklist in checklists:
#             checklist_id = self._extract_id_from_result(checklist) if isinstance(checklist, dict) else None
#             if not checklist_id:
#                 continue
            
#             # Get checklist items
#             items_action = "TRELLO_GET_CARDS_CHECKLIST_CHECK_ITEMS_BY_ID_CARD_BY_ID_CHECKLIST"
#             items_params = {"idCard": card_id, "idChecklist": checklist_id}
            
#             items_result = self._safe_execute(items_action, items_params)
#             if not items_result:
#                 continue
            
#             # Parse items
#             items = []
#             if isinstance(items_result, list):
#                 items = items_result
#             elif isinstance(items_result, dict):
#                 if "checkItems" in items_result:
#                     items = items_result["checkItems"]
#                 elif "id" in items_result:
#                     items = [items_result]
            
#             # Format tasks
#             for item in items:
#                 if isinstance(item, dict):
#                     all_tasks.append({
#                         "id": item.get("id", ""),
#                         "name": item.get("name", ""),
#                         "state": item.get("state", "incomplete"),
#                         "checklist_id": checklist_id
#                     })
        
#         return all_tasks
    
#     def update_task_status(self, card_id: str, checklist_id: str, checkitem_id: str, completed: bool) -> bool:
#         """Update task status (complete/incomplete)"""
#         action = "TRELLO_UPDATE_CARDS_CHECKLIST_CHECK_ITEMS_BY_ID_CARD_BY_ID_CHECKLIST_BY_ID_CHECKITEM"
#         params = {
#             "idCard": card_id,
#             "idChecklist": checklist_id,
#             "idCheckItem": checkitem_id,
#             "state": "complete" if completed else "incomplete"
#         }
        
#         result = self._safe_execute(action, params)
#         return result is not None
    
#     def parse_natural_language_task_update(self, query: str, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
#         """
#         Parse natural language query to determine which tasks to check/uncheck
#         Returns list of {task_id, checklist_id, card_id, action: 'check'/'uncheck'}
#         """
#         # Build task context for LLM
#         tasks_text = "\n".join([
#             f"{i+1}. {task['name']} (ID: {task['id']}, Status: {task['state']})"
#             for i, task in enumerate(tasks)
#         ])
        
#         prompt = f"""You are a task management assistant. Parse the user's query to determine which tasks should be checked or unchecked.

# Available tasks:
# {tasks_text}

# User query: {query}

# Respond with ONLY a JSON array of actions. Each action should have:
# - "task_id": the task ID
# - "action": either "check" or "uncheck"

# Example response:
# [{{"task_id": "abc123", "action": "check"}}, {{"task_id": "def456", "action": "uncheck"}}]

# If no tasks match the query, return an empty array: []

# Respond with JSON only, no other text:"""
        
#         response = self.llm.invoke(prompt)
#         response_text = response.content if hasattr(response, 'content') else str(response)
        
#         # Clean and parse JSON
#         try:
#             # Remove markdown code blocks if present
#             cleaned = re.sub(r'^```json\s*', '', response_text.strip())
#             cleaned = re.sub(r'```\s*$', '', cleaned.strip())
#             parsed = json.loads(cleaned)
            
#             if not isinstance(parsed, list):
#                 return []
            
#             # Map task names/IDs to full task info
#             results = []
#             for action_item in parsed:
#                 task_id = action_item.get("task_id")
#                 action = action_item.get("action")
                
#                 if not task_id or action not in ["check", "uncheck"]:
#                     continue
                
#                 # Find matching task
#                 task = next((t for t in tasks if t["id"] == task_id or str(t["id"]) == str(task_id)), None)
#                 if task:
#                     results.append({
#                         "task_id": task["id"],
#                         "checklist_id": task["checklist_id"],
#                         "action": action
#                     })
            
#             return results
#         except (json.JSONDecodeError, KeyError) as e:
#             print(f"Error parsing LLM response: {e}")
#             return []


# # Database will be set from main.py
# database = None

# def set_database(db):
#     global database
#     database = db

