import requests
from typing import Optional, Dict, Any


class MeetingTaskConverter:
    BASE_URL = "https://api.trello.com/1"

    def __init__(self, trello_api_key: str, trello_token: str):
        if not trello_api_key or not trello_token:
            raise ValueError("Trello API key and token are required")

        self.key = trello_api_key
        self.token = trello_token

    def _req(self, method: str, endpoint: str, params=None):
        if params is None:
            params = {}

        params["key"] = self.key
        params["token"] = self.token

        url = f"{self.BASE_URL}{endpoint}"
        r = requests.request(method, url, params=params, timeout=15)

        if not r.ok:
            raise RuntimeError(f"Trello API error {r.status_code}: {r.text}")

        return r.json()

    # ---------- LIST ----------

    def get_or_create_list(self, board_id: str, name: str) -> str:
        lists = self._req("GET", f"/boards/{board_id}/lists")

        for lst in lists:
            if lst["name"] == name and not lst["closed"]:
                return lst["id"]

        lst = self._req(
            "POST",
            f"/boards/{board_id}/lists",
            {"name": name}
        )
        return lst["id"]

    # ---------- CARD ----------

    def get_or_create_card(self, list_id: str, name: str) -> str:
        cards = self._req("GET", f"/lists/{list_id}/cards")

        for card in cards:
            if card["name"] == name and not card["closed"]:
                return card["id"]

        card = self._req(
            "POST",
            "/cards",
            {"idList": list_id, "name": name}
        )
        return card["id"]

    # ---------- CHECKLIST ----------

    def get_or_create_checklist(self, card_id: str, name="Tasks") -> str:
        checklists = self._req("GET", f"/cards/{card_id}/checklists")

        for cl in checklists:
            if cl["name"] == name:
                return cl["id"]

        cl = self._req(
            "POST",
            f"/cards/{card_id}/checklists",
            {"name": name}
        )
        return cl["id"]

    # ---------- CHECK ITEM ----------

    def add_check_item(
        self,
        checklist_id: str,
        task_text: str,
        deadline: Optional[str] = None
    ):
        if deadline:
            task_text = f"{task_text} (Due: {deadline})"

        self._req(
            "POST",
            f"/checklists/{checklist_id}/checkItems",
            {"name": task_text}
        )

    # ---------- MAIN ----------

    def convert_action_item_to_task(
        self,
        board_id: str,
        participant_name: str,
        task_text: str,
        deadline: Optional[str] = None
    ) -> Dict[str, Any]:

        try:
            list_name = f"{participant_name}'s Todo"

            list_id = self.get_or_create_list(board_id, list_name)
            card_id = self.get_or_create_card(list_id, list_name)
            checklist_id = self.get_or_create_checklist(card_id)

            self.add_check_item(checklist_id, task_text, deadline)

            return {
                "success": True,
                "list_id": list_id,
                "card_id": card_id,
                "checklist_id": checklist_id,
                "message": "Task created successfully"
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }











# iske niche se pura uncomment krdena 
# """
# Meeting Task Converter Automation
# Converts meeting action items to Trello checklist items in participant Todo lists
# """
# import sys
# import os
# from pathlib import Path
# from typing import Optional, Dict, Any
# from datetime import datetime
# import json
# import re

# # Add Composio path if it exists (for local development)
# backend_dir = Path(__file__).parent.parent
# # Try Backend/composio/python first (local repository)
# composio_path = backend_dir / "composio" / "python"
# # Fallback to Model/composio/python if Backend path doesn't exist
# if not composio_path.exists():
#     composio_path = backend_dir.parent / "Model" / "composio" / "python"

# # Try to import ComposioToolSet from installed packages FIRST (prioritize SDK over local repo)
# ComposioToolSet = None
# import_error_msg = None

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
#                     if 'meeting_task_converter' not in module_name:
#                         removed_modules[module_name] = sys.modules[module_name]
#                         del sys.modules[module_name]
                
#                 try:
#                     from plugins.langchain.composio_langchain.toolset import ComposioToolSet
#                 except ImportError as e:
#                     import_error_msg = f"Local composio path exists but import failed: {str(e)}"
#                     # Restore modules if import failed
#                     for module_name, module_obj in removed_modules.items():
#                         sys.modules[module_name] = module_obj

# # Try to import NoItemsFound
# try:
#     from composio.client.exceptions import NoItemsFound
# except ImportError:
#     # Fallback if NoItemsFound is not available
#     class NoItemsFound(Exception):
#         pass


# class MeetingTaskConverter:
#     """Service to convert meeting action items to Trello tasks"""
    
#     def __init__(self, composio_api_key: str):
#         if not composio_api_key:
#             raise ValueError("Composio API key is required")
        
#         if ComposioToolSet is None:
#             error_detail = "ComposioToolSet is not available. "
#             if composio_path.exists():
#                 error_detail += f"The local composio repository exists at {composio_path}, but ComposioToolSet could not be imported. "
#             else:
#                 error_detail += f"The local composio repository is not found at {composio_path}. "
#             error_detail += "Please ensure the Composio SDK is properly installed or the local repository is available."
#             if import_error_msg:
#                 error_detail += f" Import error: {import_error_msg}"
#             raise RuntimeError(error_detail)
        
#         self.toolset = ComposioToolSet(api_key=composio_api_key)
#         self.entity = self.toolset.get_entity()
        
#         # Check if Trello is connected
#         try:
#             connection = self.entity.get_connection(app="trello")
#             if connection.status != "ACTIVE":
#                 raise RuntimeError("Trello is not connected. Please connect Trello first.")
#         except NoItemsFound:
#             raise RuntimeError("Trello is not connected. Please connect Trello first.")
    
#     def _safe_execute(self, action_name: str, params: dict) -> Optional[object]:
#         """Safely execute Composio action"""
#         try:
#             # Get entity_id from the entity - required for write operations
#             entity_id = None
#             try:
#                 entity_id = self.entity.id
#                 print(f"Using entity_id: {entity_id} for action: {action_name}")
#             except Exception as e:
#                 print(f"Warning: Could not get entity_id: {e}")
            
#             # Execute action - always use entity_id if available
#             if entity_id:
#                 result = self.toolset.execute_action(
#                     action=action_name,
#                     params=params,
#                     entity_id=entity_id
#                 )
#             else:
#                 # Try without entity_id as fallback
#                 result = self.toolset.execute_action(action=action_name, params=params)
            
#             # Check for error responses
#             if result is None:
#                 print(f"Warning: {action_name} returned None")
#             elif isinstance(result, dict):
#                 if result.get("successfull") == False or result.get("success") == False:
#                     error_msg = result.get("error", "Unknown error")
#                     print(f"Error in {action_name}: {error_msg}")
#                     # Check for permission errors
#                     if "unauthorized" in str(error_msg).lower() or "permission" in str(error_msg).lower():
#                         raise RuntimeError(
#                             f"Trello permission error: {error_msg}. "
#                             "The connected Trello account needs to be a member of the board with write permissions. "
#                             "Please: 1) Add the Composio-connected Trello account as a member to your board in Trello, "
#                             "or 2) Reconnect Trello in Settings ensuring write permissions are granted."
#                         )
#                 elif "error" in result:
#                     error_msg = result.get("error")
#                     print(f"Warning: {action_name} returned error: {error_msg}")
            
#             return result
#         except RuntimeError:
#             # Re-raise permission errors
#             raise
#         except Exception as e:
#             print(f"Error executing {action_name}: {e}")
#             import traceback
#             traceback.print_exc()
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
    
#     def _extract_lists_from_result(self, lists_result) -> list:
#         """Extract list of lists from API response, handling various response structures"""
#         if not lists_result:
#             return []
        
#         lists = []
        
#         # Direct list
#         if isinstance(lists_result, list):
#             lists = lists_result
#             print(f"  ✓ Found direct list with {len(lists)} items")
#             return lists
        
#         # Dictionary with lists key
#         if isinstance(lists_result, dict):
#             # Check for error first
#             if "error" in lists_result:
#                 error_val = lists_result.get("error")
#                 if error_val is not None:
#                     print(f"  ⚠ Response contains error: {error_val}")
            
#             # Try data.details first (this is the actual structure from Trello API)
#             if "data" in lists_result:
#                 data = lists_result["data"]
#                 if isinstance(data, dict):
#                     # Check for details key (Trello API structure)
#                     if "details" in data and isinstance(data["details"], list):
#                         lists = data["details"]
#                         print(f"  ✓✓✓ Extracted {len(lists)} lists from data.details")
#                         return lists
#                     # Check for lists key
#                     elif "lists" in data and isinstance(data["lists"], list):
#                         lists = data["lists"]
#                         print(f"  ✓ Extracted {len(lists)} lists from data.lists")
#                         return lists
#                 elif isinstance(data, list):
#                     lists = data
#                     print(f"  ✓ Extracted {len(lists)} lists from data (direct list)")
#                     return lists
            
#             # Try other common keys
#             for key in ["lists", "result", "items", "response"]:
#                 if key in lists_result:
#                     value = lists_result[key]
#                     if isinstance(value, list):
#                         lists = value
#                         print(f"  ✓ Extracted {len(lists)} lists from key '{key}'")
#                         return lists
#                     elif isinstance(value, dict):
#                         if "lists" in value and isinstance(value["lists"], list):
#                             lists = value["lists"]
#                             print(f"  ✓ Extracted {len(lists)} lists from nested key '{key}.lists'")
#                             return lists
#                         elif "details" in value and isinstance(value["details"], list):
#                             lists = value["details"]
#                             print(f"  ✓ Extracted {len(lists)} lists from nested key '{key}.details'")
#                             return lists
            
#             # If still no lists, check if any value is a list
#             for key, value in lists_result.items():
#                 if isinstance(value, list) and len(value) > 0:
#                     # Check if first item looks like a list object
#                     if isinstance(value[0], dict) and ("id" in value[0] or "name" in value[0]):
#                         lists = value
#                         print(f"  ✓ Found list in key '{key}' with {len(lists)} items")
#                         return lists
        
#         print(f"  ⚠ No lists extracted - returning empty list")
#         return []
    
#     def get_or_create_participant_list(self, board_id: str, participant_name: str) -> Optional[str]:
#         """
#         Get or create a list named "{participant_name}'s Todo" on the board
#         Step 1: Check if list exists - if yes, return it (avoid creation)
#         Step 2: If not exists, create the list
#         Returns the list_id or None if failed
#         """
#         list_name = f"{participant_name}'s Todo"
        
#         # Retry logic to get lists - sometimes API returns None on first try
#         max_retries = 3
#         lists = []
        
#         for attempt in range(max_retries):
#             print(f"Searching for existing list: '{list_name}' on board {board_id} (attempt {attempt + 1}/{max_retries})")
#             lists_result = self._safe_execute(
#                 "TRELLO_GET_BOARDS_LISTS_BY_ID_BOARD",
#                 {"idBoard": board_id}
#             )
            
#             # Debug: print what we got
#             print(f"API response type: {type(lists_result)}, value: {lists_result}")
            
#             # If result is None, retry after a short delay
#             if lists_result is None:
#                 print(f"⚠ API returned None on attempt {attempt + 1}, retrying...")
#                 if attempt < max_retries - 1:
#                     import time
#                     time.sleep(0.5)
#                     continue
#                 else:
#                     print(f"⚠ All {max_retries} attempts returned None, proceeding with empty list")
#                     break
            
#             # Extract lists using helper function
#             lists = self._extract_lists_from_result(lists_result)
            
#             # If we got lists, break out of retry loop
#             if lists:
#                 print(f"✓ Successfully retrieved {len(lists)} lists on attempt {attempt + 1}")
#                 break
#             else:
#                 print(f"⚠ No lists extracted on attempt {attempt + 1}")
#                 if attempt < max_retries - 1:
#                     import time
#                     time.sleep(0.5)
        
#         print(f"Final result: Found {len(lists)} lists on board")
#         if lists:
#             print(f"List names: {[item.get('name', 'N/A') if isinstance(item, dict) else 'N/A' for item in lists[:10]]}")
        
#         # Search for existing list (case-insensitive and handle variations)
#         for list_item in lists:
#             if isinstance(list_item, dict):
#                 item_name = list_item.get("name", "")
#                 is_closed = list_item.get("closed", False)
#                 list_id = self._extract_id_from_result(list_item)
                
#                 # Debug each list
#                 print(f"  Checking list: '{item_name}' (closed: {is_closed}, id: {list_id})")
                
#                 # Exact match first
#                 if item_name == list_name and not is_closed:
#                     if list_id:
#                         print(f"✓✓✓ Found existing list: {list_name} ({list_id}) - WILL USE THIS")
#                         return list_id
                
#                 # Case-insensitive match as fallback
#                 if item_name.lower().strip() == list_name.lower().strip() and not is_closed:
#                     if list_id:
#                         print(f"✓✓✓ Found existing list (case-insensitive): {item_name} ({list_id}) - WILL USE THIS")
#                         return list_id
        
#         # Create new list if not found
#         print(f"⚠ No existing list found in initial search. Performing final check before creating...")
        
#         # Double-check one more time before creating (race condition protection)
#         import time
#         time.sleep(0.5)  # Longer delay to ensure API has updated
        
#         # Final check with retry
#         for final_attempt in range(2):
#             lists_result_final = self._safe_execute(
#                 "TRELLO_GET_BOARDS_LISTS_BY_ID_BOARD",
#                 {"idBoard": board_id}
#             )
            
#             if lists_result_final is None:
#                 print(f"⚠ Final check attempt {final_attempt + 1} returned None")
#                 if final_attempt < 1:
#                     time.sleep(0.5)
#                     continue
#             else:
#                 lists_final = self._extract_lists_from_result(lists_result_final)
#                 print(f"Final check found {len(lists_final)} lists")
                
#                 for list_item in lists_final:
#                     if isinstance(list_item, dict):
#                         item_name = list_item.get("name", "")
#                         is_closed = list_item.get("closed", False)
#                         if (item_name == list_name or item_name.lower().strip() == list_name.lower().strip()) and not is_closed:
#                             list_id = self._extract_id_from_result(list_item)
#                             if list_id:
#                                 print(f"✓✓✓ Found existing list on final check: {item_name} ({list_id}) - WILL USE THIS")
#                                 return list_id
#                 break
        
#         print(f"⚠⚠⚠ CONFIRMED: No existing list found. Creating new list: {list_name}")
        
#         # Now create the list
#         try:
#             create_result = self._safe_execute(
#                 "TRELLO_ADD_BOARDS_LISTS_BY_ID_BOARD",
#                 {"idBoard": board_id, "name": list_name}
#             )
#         except RuntimeError as e:
#             # Permission error - re-raise it
#             raise e
        
#         if create_result:
#             # Check if the result indicates failure
#             if isinstance(create_result, dict):
#                 if create_result.get("successfull") == False or create_result.get("success") == False:
#                     error_msg = create_result.get("error", "Unknown error")
#                     if "unauthorized" in str(error_msg).lower() or "permission" in str(error_msg).lower():
#                         raise RuntimeError(
#                             f"Trello permission denied: {error_msg}. "
#                             "Please reconnect Trello in Settings and ensure you grant write permissions."
#                         )
#                     else:
#                         raise RuntimeError(f"Failed to create list: {error_msg}")
            
#             # Try to extract ID from result
#             list_id = self._extract_id_from_result(create_result)
            
#             # If extraction failed, try parsing as string
#             if not list_id and isinstance(create_result, str) and create_result.strip():
#                 try:
#                     parsed = json.loads(create_result)
#                     list_id = self._extract_id_from_result(parsed)
#                 except Exception:
#                     pass
            
#             # If still no ID, try to find the list by name after a short delay
#             if not list_id:
#                 import time
#                 time.sleep(0.5)  # Wait a bit for Trello to process
#                 # Fetch lists again to find the newly created one
#                 try:
#                     lists_result_retry = self._safe_execute(
#                         "TRELLO_GET_BOARDS_LISTS_BY_ID_BOARD",
#                         {"idBoard": board_id}
#                     )
#                 except RuntimeError:
#                     lists_result_retry = None
                    
#                 if lists_result_retry:
#                     lists_retry = self._extract_lists_from_result(lists_result_retry)
                    
#                     for list_item in lists_retry:
#                         if isinstance(list_item, dict):
#                             item_name = list_item.get("name", "")
#                             if (item_name == list_name or item_name.lower().strip() == list_name.lower().strip()) and not list_item.get("closed", False):
#                                 list_id = self._extract_id_from_result(list_item)
#                                 if list_id:
#                                     break
            
#             if list_id:
#                 print(f"Created list: {list_name} ({list_id})")
#                 return list_id
#             else:
#                 raise RuntimeError(
#                     f"List creation may have succeeded but ID not found. "
#                     "Please check your Trello board manually and try again."
#                 )
#         else:
#             raise RuntimeError("List creation returned None/empty response. Please check Trello connection.")
        
#         # This should never be reached, but just in case
#         raise RuntimeError(f"Failed to create or find list: {list_name}")
    
#     def get_or_create_todo_card(self, list_id: str, participant_name: str) -> Optional[str]:
#         """
#         Get or create a card in the list for the participant's todos
#         Returns the card_id or None if failed
#         """
#         card_name = f"{participant_name}'s Todo"
        
#         # First, try to find existing card in the list
#         cards_result = self._safe_execute(
#             "TRELLO_GET_LISTS_CARDS_BY_ID_LIST",
#             {"idList": list_id}
#         )
        
#         if cards_result:
#             cards = []
#             if isinstance(cards_result, list):
#                 cards = cards_result
#             elif isinstance(cards_result, dict):
#                 if "cards" in cards_result:
#                     cards = cards_result["cards"]
#                 elif "data" in cards_result:
#                     data = cards_result["data"]
#                     if isinstance(data, list):
#                         cards = data
#                     elif isinstance(data, dict) and "cards" in data:
#                         cards = data["cards"]
            
#             # Search for existing card
#             for card in cards:
#                 if isinstance(card, dict):
#                     card_name_found = card.get("name", "")
#                     # Match exact name or similar (handle apostrophes)
#                     if card_name_found == card_name or card_name_found == f"{participant_name}'s Todo":
#                         card_id = self._extract_id_from_result(card)
#                         if card_id and not card.get("closed", False):
#                             print(f"Found existing card: {card_name} ({card_id})")
#                             return card_id
        
#         # Create new card if not found
#         print(f"Creating new card: {card_name}")
#         create_result = self._safe_execute(
#             "TRELLO_ADD_LISTS_CARDS_BY_ID_LIST",
#             {"idList": list_id, "name": card_name}
#         )
        
#         if create_result:
#             card_id = self._extract_id_from_result(create_result)
#             if card_id:
#                 print(f"Created card: {card_name} ({card_id})")
#                 return card_id
        
#         print(f"Failed to create or find card: {card_name}")
#         return None
    
#     def get_or_create_checklist(self, card_id: str, checklist_name: str = "Tasks") -> Optional[str]:
#         """
#         Get or create a checklist on the card
#         Returns the checklist_id or None if failed
#         """
#         # Get existing checklists
#         checklists_result = self._safe_execute(
#             "TRELLO_GET_CARDS_CHECKLISTS_BY_ID_CARD",
#             {"idCard": card_id}
#         )
        
#         if checklists_result:
#             checklists = []
#             if isinstance(checklists_result, list):
#                 checklists = checklists_result
#             elif isinstance(checklists_result, dict):
#                 if "checklists" in checklists_result:
#                     checklists = checklists_result["checklists"]
#                 elif "data" in checklists_result:
#                     data = checklists_result["data"]
#                     if isinstance(data, list):
#                         checklists = data
#                     elif isinstance(data, dict) and "checklists" in data:
#                         checklists = data["checklists"]
            
#             # Search for existing checklist
#             for checklist in checklists:
#                 if isinstance(checklist, dict):
#                     if checklist.get("name") == checklist_name:
#                         checklist_id = self._extract_id_from_result(checklist)
#                         if checklist_id:
#                             print(f"Found existing checklist: {checklist_name} ({checklist_id})")
#                             return checklist_id
        
#         # Create new checklist if not found
#         print(f"Creating new checklist: {checklist_name}")
#         create_result = self._safe_execute(
#             "TRELLO_ADD_CARDS_CHECKLISTS_BY_ID_CARD",
#             {"idCard": card_id, "name": checklist_name}
#         )
        
#         if create_result:
#             checklist_id = self._extract_id_from_result(create_result)
#             if checklist_id:
#                 print(f"Created checklist: {checklist_name} ({checklist_id})")
#                 return checklist_id
        
#         print(f"Failed to create or find checklist: {checklist_name}")
#         return None
    
#     def add_checklist_item_with_deadline(
#         self,
#         card_id: str,
#         checklist_id: str,
#         task_text: str,
#         deadline: Optional[str] = None
#     ) -> bool:
#         """
#         Add a checklist item to the checklist
#         If deadline is provided, it will be appended to the task text or set on the card
#         Returns True if successful
#         """
#         # Format task text with deadline if provided
#         formatted_task = task_text
#         if deadline:
#             try:
#                 # Parse and format deadline
#                 if isinstance(deadline, str):
#                     deadline_date = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
#                 else:
#                     deadline_date = deadline
                
#                 deadline_str = deadline_date.strftime("%Y-%m-%d")
#                 formatted_task = f"{task_text} (Due: {deadline_str})"
#             except Exception as e:
#                 print(f"Error parsing deadline: {e}, using original task text")
        
#         # Add checklist item
#         result = self._safe_execute(
#             "TRELLO_ADD_CARDS_CHECKLIST_CHECK_ITEM_BY_ID_CARD_BY_ID_CHECKLIST",
#             {
#                 "idCard": card_id,
#                 "idChecklist": checklist_id,
#                 "name": formatted_task
#             }
#         )
        
#         if result:
#             print(f"Added checklist item: {formatted_task}")
            
#             # If deadline provided, also try to set due date on card
#             # (Note: Trello checklist items don't have individual due dates,
#             # so we could create a separate card, but for now we'll just note it in the text)
#             if deadline:
#                 try:
#                     # Try to set due date on the card (this affects the whole card)
#                     # We'll skip this for now as it would affect all checklist items
#                     pass
#                 except Exception:
#                     pass
            
#             return True
        
#         print(f"Failed to add checklist item: {formatted_task}")
#         return False
    
#     def ensure_member_on_board(self, board_id: str) -> bool:
#         """
#         Ensure the connected Trello account is a member of the board
#         Returns True if already a member or successfully added, False otherwise
#         """
#         try:
#             # Get current user's member info - try different methods
#             member_id = None
            
#             # Method 1: Try with "me" as idMember
#             member_result = self._safe_execute(
#                 "TRELLO_GET_MEMBERS_BY_ID_MEMBER",
#                 {"idMember": "me"}
#             )
            
#             if member_result and isinstance(member_result, dict):
#                 member_id = member_result.get("id") or member_result.get("idMember")
            
#             # Method 2: If that doesn't work, try to get member info from board members
#             if not member_id:
#                 # Get board info which might include member info
#                 board_result = self._safe_execute(
#                     "TRELLO_BOARD_GET_BY_ID",
#                     {"id": board_id}
#                 )
                
#                 if board_result and isinstance(board_result, dict):
#                     # Check if board has member info
#                     memberships = board_result.get("memberships", [])
#                     for membership in memberships:
#                         if isinstance(membership, dict):
#                             member_info = membership.get("idMember")
#                             if member_info:
#                                 member_id = member_info.get("id") if isinstance(member_info, dict) else member_info
#                                 break
            
#             # Method 3: Get from connection info if available
#             if not member_id:
#                 try:
#                     connection = self.entity.get_connection(app="trello")
#                     # The connection might have member info in appUniqueId or connectionParams
#                     # For now, we'll skip and just check membership
#                     pass
#                 except Exception:
#                     pass
            
#             if not member_id:
#                 print("Warning: Could not get current member ID - will check board membership without it")
#                 # Continue anyway - we can still check if we can perform actions
            
#             # If we have member_id, check if member is on the board
#             if member_id:
#                 board_members_result = self._safe_execute(
#                     "TRELLO_GET_BOARDS_MEMBERS_BY_ID_BOARD",
#                     {"idBoard": board_id}
#                 )
                
#                 if board_members_result:
#                     members = []
#                     if isinstance(board_members_result, list):
#                         members = board_members_result
#                     elif isinstance(board_members_result, dict):
#                         if "members" in board_members_result:
#                             members = board_members_result["members"]
#                         elif "data" in board_members_result:
#                             data = board_members_result["data"]
#                             if isinstance(data, list):
#                                 members = data
                    
#                     # Check if current member is already on board
#                     for member in members:
#                         if isinstance(member, dict):
#                             mem_id = member.get("id") or member.get("idMember")
#                             if mem_id == member_id:
#                                 print(f"Member {member_id} is already on board {board_id}")
#                                 return True
                
#                 # Try to add member to board (if we have permission and member_id)
#                 if member_id:
#                     print(f"Attempting to add member {member_id} to board {board_id}")
#                     add_result = self._safe_execute(
#                         "TRELLO_UPDATE_BOARDS_MEMBERS_BY_ID_BOARD",
#                         {
#                             "idBoard": board_id,
#                             "idMember": member_id,
#                             "type": "normal"  # normal, admin, observer
#                         }
#                     )
                    
#                     if add_result:
#                         print(f"Successfully added member to board")
#                         return True
            
#             # If we couldn't verify/add membership, we'll try to proceed anyway
#             # The actual operation will fail with a clear error if permissions are insufficient
#             print("Could not verify/ensure board membership - proceeding with operation")
#             return True  # Return True to allow the operation to proceed and fail gracefully if needed
                
#         except Exception as e:
#             print(f"Error checking/adding board membership: {e}")
#             return False
    
#     def convert_action_item_to_task(
#         self,
#         board_id: str,
#         participant_name: str,
#         task_text: str,
#         deadline: Optional[str] = None
#     ) -> Dict[str, Any]:
#         """
#         Main method to convert an action item to a Trello task
        
#         Sequential flow:
#         0. Ensure connected account is a member of the board
#         1. Check if list "{participant_name}'s Todo" exists on board
#            - If exists: use existing list (avoid creation)
#            - If not exists: create new list
#         2. Add card to the list (existing or newly created)
#         3. Get or create checklist "Tasks" on that card
#         4. Add checklist item with task text and deadline
        
#         Returns:
#             Dict with success status and details
#         """
#         try:
#             # Step 0: Ensure we're a member of the board
#             is_member = self.ensure_member_on_board(board_id)
#             if not is_member:
#                 return {
#                     "success": False,
#                     "error": (
#                         f"The connected Trello account is not a member of the board. "
#                         f"Please add it as a member in Trello board settings. "
#                         f"Go to your Trello board → Settings → Members → Invite, "
#                         f"or make sure the Composio-connected account has board access."
#                     )
#                 }
            
#             # Step 1: Check if list exists, create if not (avoid creation if exists)
#             print(f"Step 1: Checking for existing list '{participant_name}'s Todo' on board {board_id}")
#             list_id = self.get_or_create_participant_list(board_id, participant_name)
#             if not list_id:
#                 return {
#                     "success": False,
#                     "error": f"Failed to get or create list for {participant_name}"
#                 }
            
#             # Step 2: Add card to the list (existing or newly created)
#             print(f"Step 2: Adding card to list {list_id}")
#             card_id = self.get_or_create_todo_card(list_id, participant_name)
#             if not card_id:
#                 return {
#                     "success": False,
#                     "error": f"Failed to get or create card for {participant_name}"
#                 }
            
#             # Step 3: Get or create checklist on the card
#             print(f"Step 3: Getting or creating checklist on card {card_id}")
#             checklist_id = self.get_or_create_checklist(card_id, "Tasks")
#             if not checklist_id:
#                 return {
#                     "success": False,
#                     "error": "Failed to get or create checklist"
#                 }
            
#             # Step 4: Add checklist item with task
#             print(f"Step 4: Adding task '{task_text}' to checklist {checklist_id}")
#             success = self.add_checklist_item_with_deadline(
#                 card_id,
#                 checklist_id,
#                 task_text,
#                 deadline
#             )
            
#             if success:
#                 return {
#                     "success": True,
#                     "list_id": list_id,
#                     "card_id": card_id,
#                     "checklist_id": checklist_id,
#                     "message": f"Task added to {participant_name}'s Todo list"
#                 }
#             else:
#                 return {
#                     "success": False,
#                     "error": "Failed to add checklist item"
#                 }
        
#         except RuntimeError as e:
#             # Re-raise permission/connection errors with clear messages
#             error_msg = str(e)
#             print(f"ERROR in convert_action_item_to_task: {error_msg}")
#             return {
#                 "success": False,
#                 "error": error_msg
#             }
#         except Exception as e:
#             import traceback
#             error_trace = traceback.format_exc()
#             print(f"ERROR in convert_action_item_to_task: {str(e)}")
#             print(f"Traceback: {error_trace}")
#             return {
#                 "success": False,
#                 "error": f"Failed to convert action item to task: {str(e)}"
#             }

