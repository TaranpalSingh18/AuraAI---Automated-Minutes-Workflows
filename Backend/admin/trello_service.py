"""
AdminPerspective Trello service - Assign tasks to employees using Composio
"""
import sys
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from langchain_google_genai import ChatGoogleGenerativeAI
import json
import re

# Add Composio path
backend_dir = Path(__file__).parent.parent
composio_path = backend_dir.parent / "Model" / "composio" / "python"
sys.path.insert(0, str(composio_path))

try:
    from plugins.langchain.composio_langchain.toolset import ComposioToolSet
except ImportError:
    try:
        from composio.tools.toolset import ComposioToolSet
    except ImportError:
        ComposioToolSet = None


class AdminTrelloService:
    """Service for assigning tasks to employees via Trello"""
    
    def __init__(self, composio_api_key: str, gemini_api_key: str):
        if not composio_api_key:
            raise ValueError("Composio API key is required")
        if not gemini_api_key:
            raise ValueError("Gemini API key is required")
        
        if ComposioToolSet is None:
            raise RuntimeError("ComposioToolSet not available. Please install Composio SDK.")
        
        self.sdk = ComposioToolSet(api_key=composio_api_key)
        self.llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=gemini_api_key)
    
    def _safe_execute(self, action_name: str, params: dict) -> Optional[object]:
        """Safely execute Composio action"""
        try:
            return self.sdk.execute_action(action=action_name, params=params)
        except Exception as e:
            print(f"Error executing {action_name}: {e}")
            return None
    
    def _extract_id_from_result(self, res) -> Optional[str]:
        """Extract ID from Composio result"""
        if not res:
            return None
        if isinstance(res, dict):
            if "id" in res:
                return res["id"]
            for key in ("list", "card", "checklist", "data", "result"):
                v = res.get(key)
                if isinstance(v, dict) and "id" in v:
                    return v["id"]
        try:
            text = json.dumps(res) if not isinstance(res, str) else res
            m = re.search(r'"id"\s*:\s*"([0-9a-fA-F\-]+)"', text)
            if m:
                return m.group(1)
        except Exception:
            pass
        return None
    
    def ensure_list_exists(self, board_id: str, list_name: str) -> Optional[str]:
        """Create or get list on board"""
        action = "TRELLO_ADD_BOARDS_LISTS_BY_ID_BOARD"
        params = {"idBoard": board_id, "name": list_name}
        
        res = self._safe_execute(action, params)
        list_id = self._extract_id_from_result(res)
        return list_id
    
    def get_or_create_user_card(self, board_id: str, list_id: str, user_name: str) -> Optional[str]:
        """Get or create user's Todo card"""
        card_name = f"{user_name}'s Todo"
        
        # First, try to find existing card
        action = "TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD"
        params = {"idBoard": board_id}
        
        cards_result = self._safe_execute(action, params)
        if cards_result:
            cards = []
            if isinstance(cards_result, list):
                cards = cards_result
            elif isinstance(cards_result, dict):
                if "cards" in cards_result:
                    cards = cards_result["cards"]
                elif "id" in cards_result:
                    cards = [cards_result]
            
            for card in cards:
                if isinstance(card, dict):
                    card_name_found = card.get("name", "")
                    if card_name_found == card_name or card_name_found.startswith(f"{user_name}'"):
                        card_id = self._extract_id_from_result(card)
                        if card_id:
                            return card_id
        
        # Create new card
        action = "TRELLO_ADD_CARDS"
        params = {"idList": list_id, "name": card_name}
        
        res = self._safe_execute(action, params)
        card_id = self._extract_id_from_result(res)
        return card_id
    
    def add_task_to_card(self, card_id: str, checklist_name: str, task_text: str) -> bool:
        """Add a task to card's checklist"""
        # First, get or create checklist
        checklist_id = None
        
        # Get existing checklists
        action = "TRELLO_GET_CARDS_CHECKLISTS_BY_ID_CARD"
        params = {"idCard": card_id}
        
        checklists_result = self._safe_execute(action, params)
        if checklists_result:
            checklists = []
            if isinstance(checklists_result, list):
                checklists = checklists_result
            elif isinstance(checklists_result, dict):
                if "checklists" in checklists_result:
                    checklists = checklists_result["checklists"]
                elif "id" in checklists_result:
                    checklists = [checklists_result]
            
            for checklist in checklists:
                if isinstance(checklist, dict):
                    if checklist.get("name") == checklist_name:
                        checklist_id = self._extract_id_from_result(checklist)
                        break
        
        # Create checklist if doesn't exist
        if not checklist_id:
            action = "TRELLO_ADD_CARDS_CHECKLISTS_BY_ID_CARD"
            params = {"idCard": card_id, "name": checklist_name}
            
            res = self._safe_execute(action, params)
            checklist_id = self._extract_id_from_result(res)
        
        if not checklist_id:
            return False
        
        # Add task item to checklist
        action = "TRELLO_ADD_CARDS_CHECKLIST_CHECK_ITEM_BY_ID_CARD_BY_ID_CHECKLIST"
        params = {
            "idCard": card_id,
            "idChecklist": checklist_id,
            "name": task_text
        }
        
        res = self._safe_execute(action, params)
        return res is not None
    
    def parse_task_assignment(self, query: str, available_users: List[str]) -> Dict[str, Any]:
        """
        Parse natural language query to extract: employee_name, task_description
        Returns: {employee_name: str, task_description: str}
        """
        users_text = ", ".join(available_users)
        
        prompt = f"""You are a task assignment assistant. Parse the user's query to extract:
1. The employee/team member's name
2. The task description to assign

Available team members: {users_text}

User query: {query}

Respond with ONLY a JSON object with two keys:
- "employee_name": the name of the employee (must match one from the list or be very similar)
- "task_description": the task to assign

Example response:
{{"employee_name": "John", "task_description": "Complete the backend API documentation"}}

If you cannot determine the employee name or task, use empty strings.

Respond with JSON only, no other text:"""
        
        response = self.llm.invoke(prompt)
        response_text = response.content if hasattr(response, 'content') else str(response)
        
        try:
            cleaned = re.sub(r'^```json\s*', '', response_text.strip())
            cleaned = re.sub(r'```\s*$', '', cleaned.strip())
            parsed = json.loads(cleaned)
            
            employee_name = parsed.get("employee_name", "").strip()
            task_description = parsed.get("task_description", "").strip()
            
            # Try to match employee name to available users (fuzzy match)
            matched_name = None
            for user in available_users:
                if user.lower() == employee_name.lower() or employee_name.lower() in user.lower():
                    matched_name = user
                    break
            
            return {
                "employee_name": matched_name or employee_name,
                "task_description": task_description
            }
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing LLM response: {e}")
            return {
                "employee_name": "",
                "task_description": ""
            }


# Database will be set from main.py
database = None

def set_database(db):
    global database
    database = db

