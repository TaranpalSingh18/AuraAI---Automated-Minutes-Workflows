# trello.py
import os
import sys
import time
import json
import re
from typing import List, Optional

# Make sure Python can see your local composio repo (0.6.19)
sys.path.insert(0, r"D:/minor/Model/composio/python")

# Composio/plugin imports (0.6.19 layout)
from composio import Action, App  # keeps top-level import available if used
from plugins.langchain.composio_langchain.toolset import ComposioToolSet

# Your existing helpers (tasks.py should define participants list and answer/transcript)
from tasks import get_task, participants, answer  # expects these to exist
# If you named them differently, adjust the import or variable names accordingly.

# env
COMPOSIO_API_KEY = os.getenv("COMPOSIO_API_KEY")
BOARD_ID = os.getenv("BOARD_ID")

if not COMPOSIO_API_KEY or not BOARD_ID:
    raise RuntimeError("Please set COMPOSIO_API_KEY and BOARD_ID in your environment.")

# init sdk
sdk = ComposioToolSet(api_key=COMPOSIO_API_KEY)

# ------------- Utility helpers -------------


def _extract_id_from_result(res) -> Optional[str]:
    """Flexible extraction of an 'id' string from Composio action result."""
    if not res:
        return None
    # common: dict with id
    if isinstance(res, dict):
        if "id" in res and isinstance(res["id"], str):
            return res["id"]
        # nested shapes
        for key in ("list", "card", "checklist", "data", "result"):
            v = res.get(key, None)
            if isinstance(v, dict) and "id" in v:
                return v["id"]
    # try to stringify and regex an id-like token
    try:
        text = json.dumps(res)
    except Exception:
        text = str(res)
    m = re.search(r'"id"\s*:\s*"([0-9a-fA-F\-]+)"', text)
    if m:
        return m.group(1)
    # common numeric id
    m2 = re.search(r'"id"\s*:\s*([0-9]+)', text)
    if m2:
        return m2.group(1)
    return None


def _safe_execute(action_name: str, params: dict) -> Optional[object]:
    """Call sdk.execute_action and catch errors, returning None on failure."""
    try:
        return sdk.execute_action(action=action_name, params=params)
    except Exception as e:
        print(f"execute_action('{action_name}') raised: {e}")
        return None


# ------------- Discovery of actions -------------


def discover_actions(max_preview_chars: int = 2000) -> List[str]:
    """
    Try to discover available actions / metadata on the SDK.
    Returns a list of action names (strings).
    """
    discovered = set()

    # 1) Check common introspection methods on sdk
    for attr in ("get_metadata", "metadata", "get_actions", "get_action_metadata", "list_actions", "actions"):
        fn = getattr(sdk, attr, None)
        if callable(fn):
            try:
                meta = fn()
            except Exception as e:
                # Some metadata calls may require args or api_key; ignore errors
                print(f"sdk.{attr}() raised: {e}")
                meta = None
            if meta:
                # meta might be dict/list: try to pick up strings that look like action enums
                meta_text = json.dumps(meta) if not isinstance(meta, str) else meta
                # find potential action names (ALL_CAPS underscore words)
                for m in re.findall(r'"([A-Z0-9_]{5,50})"', meta_text):
                    discovered.add(m)
                # also explicitly search for words with TRELLO or CARD or CHECKLIST
                for m in re.findall(r'([A-Z0-9_]*TRELLO[A-Z0-9_]*)', meta_text):
                    discovered.add(m)
                for m in re.findall(r'([A-Z0-9_]*CARD[A-Z0-9_]*)', meta_text):
                    discovered.add(m)
                for m in re.findall(r'([A-Z0-9_]*CHECKLIST[A-Z0-9_]*)', meta_text):
                    discovered.add(m)


    candidates = [
        "TRELLO_ADD_CARDS"
    ]
    for c in candidates:
        discovered.add(c)

    return sorted(discovered)


def ensure_list_exists(list_name: str, create_action: str = "TRELLO_ADD_BOARDS_LISTS_BY_ID_BOARD") -> Optional[str]:
    """
    Create/ensure a list on BOARD_ID with given name. Returns list_id or None.
    Uses the create_action (string).
    """
    params = {"idBoard": BOARD_ID, "name": list_name}
    res = _safe_execute(create_action, params)
    list_id = _extract_id_from_result(res)
    if list_id:
        return list_id
    # Some SDKs return full object or string - try some fallbacks:
    if isinstance(res, str) and res.strip():
        # maybe returned JSON string
        try:
            parsed = json.loads(res)
            lid = _extract_id_from_result(parsed)
            if lid:
                return lid
        except Exception:
            pass
    # If the action apparently succeeded but returned no id, try to find list by name (best-effort)
    print(f"[ensure_list_exists] Could not determine list id from result: {res}")
    return None

def try_create_card_in_list(list_id: str, card_name: str) -> Optional[str]:
    """
    Create a Trello card in the given list using the TRELLO_ADD_CARDS action.
    Returns the created card_id if successful, otherwise None.
    """
    action_slug = "TRELLO_ADD_CARDS"
    params = {
        "idList": list_id,
        "name": card_name
    }

    print(f"Creating card '{card_name}' in list '{list_id}' using {action_slug}...")
    res = _safe_execute(action_slug, params)
    card_id = _extract_id_from_result(res)

    if card_id:
        print(f"✅ Card created successfully! Card ID: {card_id}")
        return card_id
    else:
        print(f"❌ Failed to create card '{card_name}'. Response: {res}")
        return None



def try_add_checklist_to_card(card_id: str, checklist_name: str, items: List[str]) -> bool:
    """
    1) Create a checklist on the card using TRELLO_ADD_CARDS_CHECKLISTS_BY_ID_CARD (idCard, name)
    2) Add each item using TRELLO_ADD_CARDS_CHECKLIST_CHECK_ITEM_BY_ID_CARD_BY_ID_CHECKLIST (idCard, idChecklist, name)
    Returns True if at least one item was added successfully.
    """
    if not card_id:
        print("try_add_checklist_to_card: missing card_id")
        return False

    # 1) create checklist
    create_checklist_action = "TRELLO_ADD_CARDS_CHECKLISTS_BY_ID_CARD"
    print(f"Creating checklist '{checklist_name}' on card {card_id} using {create_checklist_action}...")
    res_create = _safe_execute(create_checklist_action, {"idCard": card_id, "name": checklist_name})

    # extract checklist id
    checklist_id = _extract_id_from_result(res_create)
    # fallback parsing if extractor failed
    if not checklist_id:
        try:
            if isinstance(res_create, str):
                parsed = json.loads(res_create)
                checklist_id = _extract_id_from_result(parsed)
            elif isinstance(res_create, dict):
                checklist_id = _extract_id_from_result(res_create)
        except Exception:
            checklist_id = None

    if not checklist_id:
        print(f"Failed to create checklist (no id in response). Response: {res_create}")
        return False

    print(f"Checklist created with id: {checklist_id}")

    # 2) add items using exact slug
    add_item_action = "TRELLO_ADD_CARDS_CHECKLIST_CHECK_ITEM_BY_ID_CARD_BY_ID_CHECKLIST"
    added_any = False

    for item in items:
        item = item.strip()
        if not item:
            continue
        params = {"idCard": card_id, "idChecklist": checklist_id, "name": item}
        print(f"Adding checklist item to checklist {checklist_id}: '{item}'")
        res_item = _safe_execute(add_item_action, params)

        if res_item:
            item_id = _extract_id_from_result(res_item)
            if item_id or isinstance(res_item, dict):
                print(f" -> added: '{item}' (response id: {item_id})")
                added_any = True
            else:
                # truthy response with no id still treated as success
                print(f" -> added (no-id response): {str(res_item)[:120]}")
                added_any = True
        else:
            print(f" -> failed to add item '{item}'. Response: {res_item}")
        time.sleep(0.25)  # throttle

    return added_any


def main():
    print("Starting Trello sync (cards via TRELLO_ADD_CARDS, checklist via TRELLO_ADD_CARDS_CHECKLISTS_BY_ID_CARD + item slug)...")

    create_list_action = "TRELLO_ADD_BOARDS_LISTS_BY_ID_BOARD"
    card_action_slug = "TRELLO_ADD_CARDS"

    for name in participants:
        list_name = f"{name}'s Todo"
        print(f"\n[{name}] Ensuring list '{list_name}'...")
        list_id = ensure_list_exists(list_name, create_action=create_list_action)
        if not list_id:
            print(f"[{name}] Could not create/obtain list id. Skipping participant.")
            continue
        print(f"[{name}] Using list id: {list_id}")

        # create card
        card_name = f"{name}'s Card"
        print(f"[{name}] Creating card '{card_name}' using {card_action_slug} ...")
        card_id = try_create_card_in_list(list_id=list_id, card_name=card_name)
        if not card_id:
            print(f"[{name}] Failed to create card with action {card_action_slug}. Skipping checklist creation.")
            continue
        print(f"[{name}] Created card id: {card_id}")

        # fetch tasks
        print(f"[{name}] Fetching tasks via get_task(...)")
        raw_tasks = ""
        try:
            raw_tasks = get_task(answer, name)
        except Exception as e:
            print(f"[{name}] get_task raised: {e}")
            raw_tasks = ""

        # parse tasks into list
        tasks_list: List[str] = []
        if raw_tasks:
            txt = raw_tasks.strip()
            parsed = None
            try:
                parsed = json.loads(txt)
            except Exception:
                try:
                    import ast
                    parsed = ast.literal_eval(txt)
                except Exception:
                    parsed = None
            if isinstance(parsed, list):
                tasks_list = [str(x).strip() for x in parsed if str(x).strip()]
            else:
                lines = [ln.strip() for ln in txt.splitlines() if ln.strip()]
                cleaned = [re.sub(r'^\s*Task[-\s]*\d+\s*[:.-]*\s*', '', ln, flags=re.IGNORECASE) for ln in lines]
                tasks_list = [c for c in cleaned if c]

        if not tasks_list:
            print(f"[{name}] No tasks parsed from LLM result; skipping checklist creation for card {card_id}.")
            continue

        print(f"[{name}] Parsed {len(tasks_list)} tasks — adding checklist items using new slugs...")
        ok = try_add_checklist_to_card(card_id=card_id, checklist_name=f"{name}'s Tasks", items=tasks_list)
        if ok:
            print(f"[{name}] Checklist items added successfully ({len(tasks_list)} items).")
        else:
            print(f"[{name}] Failed to add checklist items via slug.")

        time.sleep(1.0)

# If this file is run directly
if __name__ == "__main__":
    main()
# d_card_of_respective_participants(participants, answer)  # answer is your summarized transcript

# create_lists_from_participants(particpants=participants)


# KEY = os.environ.get("TRELLO_KEY")
# TOKEN = os.environ.get("TRELLO_TOKEN")


# TRELLO_BASE = "https://api.trello.com/1"



# class TRELLO:
#     def __init__(self, api_key: str, **kwargs):
#         self.api_key = api_key
#         # composio toolset (used for create_board_from_query in your original file)
#         self.prompt_toolset = composio_langchain.ComposioToolSet(api_key=api_key)
#         self.llm = globals().get("llm", None)

#     # ---------- LLM helpers ----------
#     def clean_llm_json_response(self, raw: str):
#         if not isinstance(raw, str):
#             raise ValueError("clean_llm_json_response expects a string")
#         cleaned = re.sub(r"^(```|''')\s*json\s*", "", raw.strip(), flags=re.IGNORECASE)
#         cleaned = re.sub(r"(```|''')\s*$", "", cleaned.strip())
#         return json.loads(cleaned)

#     def _unwrap_llm_response(self, resp):
#         """
#         Minimal helper: return a plain string from common LLM response shapes.
#         Supports:
#          - plain str
#          - objects with .content or .text (e.g., AIMessage)
#          - LangChain-like .generations -> [[Generation(text=...)]]
#          - lists of strings
#          - fallback: str(resp)
#         """
#         # plain string
#         if isinstance(resp, str):
#             return resp

#         # objects with content/text attributes (AIMessage, etc.)
#         if hasattr(resp, "content"):
#             try:
#                 return getattr(resp, "content")
#             except Exception:
#                 pass
#         if hasattr(resp, "text"):
#             try:
#                 return getattr(resp, "text")
#             except Exception:
#                 pass

#         # LangChain-like .generations
#         if hasattr(resp, "generations"):
#             try:
#                 gens = getattr(resp, "generations")
#                 if gens and isinstance(gens, list) and gens[0]:
#                     # typical shape: generations -> [ [Generation(text=...)] ]
#                     first = gens[0]
#                     if isinstance(first, list) and first and hasattr(first[0], "text"):
#                         return first[0].text
#                     # or gens -> [Generation...] (flat)
#                     if hasattr(first, "text"):
#                         return first.text
#             except Exception:
#                 pass

#         # list of strings
#         if isinstance(resp, list) and resp:
#             if isinstance(resp[0], str):
#                 return resp[0]
#             # sometimes list contains dicts with 'text' or 'content'
#             first = resp[0]
#             if isinstance(first, dict):
#                 for key in ("content", "text", "name"):
#                     if key in first and isinstance(first[key], str):
#                         return first[key]

#         # fallback: coerce to string
#         try:
#             return str(resp)
#         except Exception:
#             return ""

#     # ---------- Composio-based board creation (kept from your original file) ----------
#     def create_board(self, query: str):
#         """
#         Single-shot: extract board/workspace name from `query` using the LLM,
#         then call Composio's TRELLO_ADD_BOARDS to create it and return the board name only.
#         """
#         prompt = (
#             "You are a text extractor. Given a Trello-related user query, "
#             "return only the board or workspace name in plain text (no JSON, no code fences).\n\n"
#             "Examples:\n"
#             "Query: I want you to create a workspace named as Taran\n"
#             "Response: Taran's workspace\n\n"
#             "Query: Create a board named as Sigmoid\n"
#             "Response: Sigmoid's workspace\n\n"
#             f"Now extract the board/workspace name from this query:\n\n{query}\n\n"
#             "Return just the name (one short string)."
#         )

#         raw_resp = llm.invoke(prompt)
#         board_name = self._unwrap_llm_response(raw_resp)

#         board_name = (board_name or "").strip()
#         board_name = re.sub(r"^(```|''')\s*|(```|''')\s*$", "", board_name)

#         toolset = getattr(self, "prompt_toolset", None) or getattr(self, "toolset", None)
#         if toolset is None:
#             return "Error: no ComposioToolSet found on the instance (expected self.prompt_toolset or self.toolset)."

#         try:
#             tools = toolset.get_tools(actions=[Action.TRELLO_ADD_BOARDS])
#             if not tools:
#                 return "Error: ComposioToolSet did not return any tools for TRELLO_ADD_BOARDS."
#             tool = tools[0]
#         except Exception as e:
#             return f"Error while retrieving composio tool: {e}"

#         try:
#             result = tool.run({"name": board_name})
#             result_key = result["name"] if isinstance(result, dict) and "name" in result else board_name
#             return str(result_key).strip()
#         except Exception as e:
#             return f"Error creating board via composio tool: {e}"

#     # ---------- Trello HTTP helpers ----------
#     @staticmethod
#     def extract_workspace_identifier(workspace_input: str) -> str:
#         """
#         Accepts:
#           - full URL like "https://trello.com/w/userworkspace57275986/home"
#           - short name like "userworkspace57275986"
#           - displayName or org-id (function will try sensible heuristics)
#         Returns a candidate identifier (shortName or original string).
#         """
#         if not isinstance(workspace_input, str):
#             return ""
#         # Try to extract the `userworkspace...` part from a URL
#         m = re.search(r"trello\.com/(?:w|c|b|enterprise)/([^/]+)", workspace_input)
#         if m:
#             return m.group(1)
#         # If user pasted a full /orgs/ url pattern, extract last path segment
#         m2 = re.search(r"trello\.com/[^/]+/([^/?#]+)", workspace_input)
#         if m2:
#             return m2.group(1)
#         # Otherwise return raw input (maybe it's already the shortName or id)
#         return workspace_input.strip()

#     def _trello_get(
#         self, path: str, key: str, token: str, params: Optional[dict] = None, timeout: int = 15
#     ) -> Any:
#         """
#         Small wrapper for Trello GET calls. Caller must pass Trello `key` and `token`.
#         path should begin with a leading slash, e.g. "/organizations/{id}/boards"
#         """
#         if not key or not token:
#             raise ValueError("Trello key and token are required")
#         url = f"{TRELLO_BASE}{path}"
#         params = params.copy() if params else {}
#         params.update({"key": key, "token": token})
#         resp = requests.get(url, params=params, timeout=timeout)
#         resp.raise_for_status()
#         return resp.json()

#     def _trello_post(
#         self, path: str, key: str, token: str, data: Optional[dict] = None, timeout: int = 15
#     ) -> Any:
#         """
#         Small wrapper for Trello POST calls. Caller must pass Trello `key` and `token`.
#         path should begin with a leading slash, e.g. "/lists" or "/cards"
#         """
#         if not key or not token:
#             raise ValueError("Trello key and token are required")
#         url = f"{TRELLO_BASE}{path}"
#         data = data.copy() if data else {}
#         data.update({"key": key, "token": token})
#         resp = requests.post(url, data=data, timeout=timeout)
#         resp.raise_for_status()
#         return resp.json()

#     # ---------- Board / list fetchers ----------
#     def fetch_workspace_boards(
#         self, key: str, token: str, workspace_input: str, include_closed: bool = False
#     ) -> List[Dict[str, Any]]:
#         """
#         Fetch boards for a given workspace.

#         workspace_input can be:
#           - full trello UI link (like the one you shared)
#           - workspace short name (e.g. userworkspace57275986)
#           - workspace displayName (less reliable; we try shortName first)

#         Returns a list of boards with fields: id, name, url, closed.
#         """
#         candidate = self.extract_workspace_identifier(workspace_input)
#         org_id = None

#         # Try candidate as organization shortName or id
#         try:
#             # validate organization exists
#             _ = self._trello_get(
#                 f"/organizations/{candidate}", key, token, params={"fields": "id,displayName"}
#             )
#             org_id = candidate
#         except requests.HTTPError:
#             # fallback: list member's orgs and try to match displayName / id
#             orgs = self._trello_get(
#                 "/members/me/organizations", key, token, params={"fields": "id,displayName,desc"}
#             )
#             org_match = None
#             lc = candidate.lower()
#             for o in orgs:
#                 if o.get("displayName", "").lower() == lc:
#                     org_match = o
#                     break
#             if not org_match:
#                 for o in orgs:
#                     if lc in o.get("displayName", "").lower() or lc in o.get("id", ""):
#                         org_match = o
#                         break
#             if not org_match:
#                 raise ValueError(
#                     f"Could not resolve workspace '{workspace_input}'. Available orgs: {[o.get('displayName') for o in orgs]}"
#                 )
#             org_id = org_match["id"]

#         # fetch boards
#         boards = self._trello_get(
#             f"/organizations/{org_id}/boards", key, token, params={"fields": "id,name,url,closed"}
#         )
#         if not include_closed:
#             boards = [b for b in boards if not b.get("closed", False)]
#         compact = [{"id": b["id"], "name": b["name"], "url": b.get("url"), "closed": b.get("closed", False)} for b in boards]
#         return compact

#     def fetch_workspace_board_map(
#         self, key: str, token: str, workspace_input: str, include_closed: bool = False
#     ) -> Dict[str, str]:
#         """
#         Returns a mapping of board_name -> board_id for the given workspace.
#         If multiple boards share the same name, the first occurrence is used.
#         """
#         boards = self.fetch_workspace_boards(key, token, workspace_input, include_closed=include_closed)
#         board_map: Dict[str, str] = {}
#         for b in boards:
#             name = b.get("name", "").strip()
#             bid = b.get("id")
#             if name and bid and name not in board_map:
#                 board_map[name] = bid
#         return board_map

#     def fetch_workspace_board_ids(
#         self, key: str, token: str, workspace_input: str, include_closed: bool = False
#     ) -> List[str]:
#         """
#         Minimal variant that returns only board ids (deduplicated, preserving order).
#         """
#         boards = self.fetch_workspace_boards(key, token, workspace_input, include_closed=include_closed)
#         # deduplicate while preserving order (just in case)
#         seen = set()
#         ids = []
#         for b in boards:
#             bid = b.get("id")
#             if bid and bid not in seen:
#                 seen.add(bid)
#                 ids.append(bid)
#         return ids

#     # ---------- Create lists ----------
#     def create_list_on_board(self, key: str, token: str, board_id: str, list_name: str, pos: str = "top") -> Dict[str, Any]:
#         """
#         Create a new list on the specified board.
#         pos: "top", "bottom", or a float index (Trello accepts "top"/"bottom"/"1").
#         Returns the created list JSON from Trello.
#         """
#         if not board_id:
#             raise ValueError("board_id is required")
#         if not list_name or not isinstance(list_name, str):
#             raise ValueError("list_name must be a non-empty string")
#         payload = {"name": list_name.strip(), "idBoard": board_id, "pos": pos}
#         return self._trello_post("/lists", key, token, data=payload)

#     # ---------- LLM-based extractors for board/list/card ----------
#     def _extract_board_and_list_from_query(self, query: str) -> Dict[str, str]:
#         """
#         Uses the LLM to extract both the target board name and the desired list name
#         from a freeform user query.

#         Returns a dict: {"board": "<board-name-or-empty>", "list": "<list-name-or-empty>"}.
#         Strategy:
#          - Ask the LLM to return JSON only: {"board":"...","list":"..."}.
#          - Try to parse JSON; if parsing fails, run regex heuristics to recover likely values.
#         """
#         model = getattr(self, "llm", None) or globals().get("llm", None)
#         if model is None:
#             raise RuntimeError("No LLM available on this instance (self.llm missing)")

#         prompt = (
#             "Extract the target Trello board name and the new list name from the user's request. "
#             "Reply ONLY with a JSON object and nothing else, with exactly two keys: "
#             "\"board\" and \"list\". Use empty string for any value you cannot find.\n\n"
#             "Examples:\n"
#             'Input: "Please add a list named \"Sprint Backlog\" to the Product board."\n'
#             'Output: {"board":"Product","list":"Sprint Backlog"}\n\n'
#             'Input: "Create a list called Done on my Marketing board."\n'
#             'Output: {"board":"Marketing","list":"Done"}\n\n'
#             f"Now extract from this user query:\n{query}\n\n"
#             "Output JSON:"
#         )

#         raw = model.invoke(prompt)
#         text = self._unwrap_llm_response(raw) or ""
#         text = text.strip()

#         # Try to parse JSON first (best outcome)
#         try:
#             cleaned = text
#             cleaned = re.sub(r"^(```|''')\s*json\s*", "", cleaned, flags=re.IGNORECASE)
#             cleaned = re.sub(r"^(```|''')", "", cleaned)
#             cleaned = re.sub(r"(```|''')\s*$", "", cleaned)
#             obj = json.loads(cleaned)
#             board = (obj.get("board") or "").strip() if isinstance(obj, dict) else ""
#             lst = (obj.get("list") or "").strip() if isinstance(obj, dict) else ""
#             return {"board": board, "list": lst}
#         except Exception:
#             # fallback heuristics
#             board = ""
#             lst = ""

#             # 1) quoted strings heuristic: capture all quoted phrases
#             quoted = re.findall(r"['\"]([^'\"]{1,200})['\"]", text if text else query)
#             if quoted:
#                 # Heuristic: if two quoted phrases, assume one is list and one is board.
#                 if len(quoted) >= 2:
#                     first, second = quoted[0].strip(), quoted[1].strip()
#                     idx_second = (query or "").find(quoted[1])
#                     ctx = (query or "")[max(0, idx_second - 20) : idx_second + len(quoted[1]) + 20].lower()
#                     if "board" in ctx or "on" in ctx or "to the" in ctx:
#                         board, lst = second, first
#                     else:
#                         lst, board = first, second
#                 else:
#                     single = quoted[0].strip()
#                     qlower = (query or "").lower()
#                     if re.search(r"\b(list|card|add|create|named|called)\b", qlower):
#                         lst = single
#                     idx = (query or "").find(quoted[0])
#                     ctx = (query or "")[max(0, idx - 20) : idx + len(quoted[0]) + 20].lower()
#                     if "board" in ctx or "on the" in ctx or "on " in ctx:
#                         board = single

#             # 2) pattern heuristics
#             if not lst:
#                 m = re.search(
#                     r"(?:add|create|make)\s+(?:a\s+)?list\s+(?:called|named)?\s*[:\-]?\s*['\"]?([^'\"\n,]+)['\"]?",
#                     query,
#                     flags=re.IGNORECASE,
#                 )
#                 if m:
#                     lst = m.group(1).strip()
#             if not board:
#                 m2 = re.search(
#                     r"(?:to|on|in)\s+(?:the\s+)?(?:board\s+)?['\"]?([^'\"\n,]+)['\"]?", query, flags=re.IGNORECASE
#                 )
#                 if m2:
#                     board = m2.group(1).strip()

#             # 3) last ditch
#             if not board:
#                 m3 = re.search(
#                     r"board\s+(?:named|called)?\s*['\"]?([^'\"\n,]+)['\"]?", query, flags=re.IGNORECASE
#                 )
#                 if m3:
#                     board = m3.group(1).strip()

#             return {"board": board, "list": lst}

#     def create_list_from_query(
#         self,
#         query: str,
#         key: str,
#         token: str,
#         workspace_input: str,
#         include_closed: bool = False,
#         pos: str = "top",
#         fallback_list_name: Optional[str] = None,
#     ) -> Any:
#         """
#         High-level helper that:
#           - Extracts board name and list name from the query (LLM + heuristics)
#           - Looks up the board id in workspace (board map)
#           - Creates the new list on the board using the extracted list name (or fallback_list_name)
#         Returns the created list JSON on success or raises informative ValueError on failure.
#         """
#         parsed = self._extract_board_and_list_from_query(query)
#         board_name = (parsed.get("board") or "").strip()
#         list_name = (parsed.get("list") or "").strip()

#         # If LLM didn't find a list name, use fallback_list_name if provided
#         if not list_name:
#             if fallback_list_name:
#                 list_name = fallback_list_name.strip()
#             else:
#                 raise ValueError(
#                     "Could not extract a list name from the query and no fallback_list_name provided. "
#                     "Example query: \"Add a list called 'Sprint Backlog' to the Product board.\""
#                 )

#         # 1) fetch board map and try to resolve the board_name
#         board_map = self.fetch_workspace_board_map(key, token, workspace_input, include_closed=include_closed)

#         board_id = None
#         if board_name:
#             # try exact match
#             if board_name in board_map:
#                 board_id = board_map[board_name]
#             else:
#                 # case-insensitive
#                 lower_map = {k.lower(): v for k, v in board_map.items()}
#                 board_id = lower_map.get(board_name.lower())

#         # 2) fuzzy/substring fallback: try to find unique board by substring tokens from query
#         if not board_id:
#             qtokens = [t.strip() for t in re.split(r"[,\s]+", query) if len(t.strip()) > 2]
#             candidates = []
#             for name, bid in board_map.items():
#                 lname = name.lower()
#                 for tok in qtokens:
#                     if tok.lower() in lname:
#                         candidates.append((name, bid))
#                         break
#             if len(candidates) == 1:
#                 board_id = candidates[0][1]
#                 board_name = candidates[0][0]
#             elif len(candidates) > 1:
#                 for name, bid in candidates:
#                     if name.lower().startswith(qtokens[0].lower()):
#                         board_id = bid
#                         board_name = name
#                         break

#         if not board_id:
#             available = list(board_map.keys())
#             raise ValueError(
#                 f"Could not determine target board from query '{query}'. Extracted board name: '{board_name}'. Available boards: {available}"
#             )

#         # 3) create the list
#         created = self.create_list_on_board(key, token, board_id, list_name, pos=pos)
#         return created

#     # ---------- Card helpers (board+list+card extraction + creation) ----------
#     def _extract_board_list_card_from_query(self, query: str) -> Dict[str, str]:
#         """
#         Ask the LLM to extract board, list and card names from the query.
#         Returns: {"board": "...", "list": "...", "card": "..."} (values may be empty strings).
#         Uses JSON-first strategy, then regex/heuristics fallback.
#         """
#         model = getattr(self, "llm", None) or globals().get("llm", None)
#         if model is None:
#             raise RuntimeError("No LLM available on this instance (self.llm missing)")

#         prompt = (
#             "Extract the Trello board name, the target list name, and the card title from the user's request. "
#             "Reply ONLY with a JSON object and nothing else, with exactly three keys: "
#             '"board", "list", and "card". Use empty string for any value you cannot find.\n\n'
#             "Examples:\n"
#             'Input: "Add a card called \"dinner\" to the Todo list on Sujal\\\'s board."\n'
#             'Output: {"board":"Sujal","list":"Todo","card":"dinner"}\n\n'
#             f"Now extract from this user query:\n{query}\n\nOutput JSON:"
#         )

#         raw = model.invoke(prompt)
#         text = self._unwrap_llm_response(raw) or ""
#         text = text.strip()

#         # try parse JSON first
#         try:
#             cleaned = text
#             cleaned = re.sub(r"^(```|''')\s*json\s*", "", cleaned, flags=re.IGNORECASE)
#             cleaned = re.sub(r"^(```|''')", "", cleaned)
#             cleaned = re.sub(r"(```|''')\s*$", "", cleaned)
#             obj = json.loads(cleaned)
#             board = (obj.get("board") or "").strip() if isinstance(obj, dict) else ""
#             lst = (obj.get("list") or "").strip() if isinstance(obj, dict) else ""
#             card = (obj.get("card") or "").strip() if isinstance(obj, dict) else ""
#             return {"board": board, "list": lst, "card": card}
#         except Exception:
#             # fallback heuristics
#             board = ""
#             lst = ""
#             card = ""

#             # capture quoted phrases first — usually card/list names are quoted
#             quoted = re.findall(r"['\"]([^'\"]{1,200})['\"]", text if text else query)
#             if quoted:
#                 if len(quoted) >= 3:
#                     card, lst, board = quoted[0].strip(), quoted[1].strip(), quoted[2].strip()
#                 elif len(quoted) == 2:
#                     qlower = (query or "").lower()
#                     if "list" in qlower or "todo" in qlower or "done" in qlower:
#                         card, lst = quoted[0].strip(), quoted[1].strip()
#                     else:
#                         idx2 = (query or "").find(quoted[1])
#                         ctx = (query or "")[max(0, idx2 - 20) : idx2 + len(quoted[1]) + 20].lower()
#                         if "board" in ctx:
#                             card, board = quoted[0].strip(), quoted[1].strip()
#                         else:
#                             card, lst = quoted[0].strip(), quoted[1].strip()
#                 else:
#                     single = quoted[0].strip()
#                     qlower = (query or "").lower()
#                     if re.search(r"\b(card|add|create|todo|task|add a)\b", qlower):
#                         card = single
#                     idx = (query or "").find(quoted[0])
#                     ctx = (query or "")[max(0, idx - 20) : idx + len(quoted[0]) + 20].lower()
#                     if "list" in ctx or "todo" in ctx or "done" in ctx:
#                         lst = single
#                     if "board" in ctx or "on" in ctx or "to" in ctx:
#                         board = single

#             # additional pattern matching
#             if not card:
#                 m = re.search(
#                     r"(?:add|create|make)\s+(?:a\s+)?card\s+(?:called|named)?\s*[:\-]?\s*['\"]?([^'\"\n,]+)['\"]?",
#                     query,
#                     flags=re.IGNORECASE,
#                 )
#                 if m:
#                     card = m.group(1).strip()
#                 else:
#                     m2 = re.search(
#                         r"(['\"]?)([^'\"\n]+?)\1\s+(?:to|into|in)\s+(?:the\s+)?([^\n]+?)(?:\s+list|\s+board|$)",
#                         query,
#                         flags=re.IGNORECASE,
#                     )
#                     if m2 and not card:
#                         card = m2.group(2).strip()

#             if not lst:
#                 m = re.search(
#                     r"(?:list|lists)\s+(?:called|named)?\s*['\"]?([^'\"\n,]+)['\"]?", query, flags=re.IGNORECASE
#                 )
#                 if m:
#                     lst = m.group(1).strip()
#                 else:
#                     m2 = re.search(
#                         r"(?:to|on|in)\s+(?:the\s+)?([A-Za-z0-9 _-]{2,60})\s+list\b", query, flags=re.IGNORECASE
#                     )
#                     if m2:
#                         lst = m2.group(1).strip()

#             if not board:
#                 m3 = re.search(
#                     r"(?:board\s+(?:named|called)?\s*['\"]?([^'\"\n,]+)['\"]?)", query, flags=re.IGNORECASE
#                 )
#                 if m3:
#                     board = m3.group(1).strip()
#                 else:
#                     m4 = re.search(r"of\s+([A-Za-z0-9 _-]{2,60})['\s]*board", query, flags=re.IGNORECASE)
#                     if m4:
#                         board = m4.group(1).strip()

#             return {"board": board, "list": lst, "card": card}

#     def get_lists_on_board(self, key: str, token: str, board_id: str, include_closed: bool = False) -> List[Dict[str, Any]]:
#         """
#         Return lists for a given board_id. Each item: {"id":..., "name":..., "closed":...}
#         """
#         if not board_id:
#             raise ValueError("board_id is required")
#         lists = self._trello_get(f"/boards/{board_id}/lists", key, token, params={"fields": "id,name,closed"})
#         if not include_closed:
#             lists = [l for l in lists if not l.get("closed", False)]
#         return [{"id": l["id"], "name": l["name"], "closed": l.get("closed", False)} for l in lists]

#     def find_list_id_by_name(self, lists: List[Dict[str, Any]], list_name: str) -> Optional[str]:
#         """
#         Try to find list id by list_name using exact, case-insensitive and substring matching.
#         Returns first match id or None.
#         """
#         if not list_name:
#             return None
#         # exact
#         for l in lists:
#             if l.get("name") == list_name:
#                 return l.get("id")
#         # case-insensitive
#         lname_map = {l.get("name", "").lower(): l.get("id") for l in lists}
#         lid = lname_map.get(list_name.lower())
#         if lid:
#             return lid
#         # substring token match
#         tokens = [t for t in re.split(r"\s+", list_name) if t]
#         for l in lists:
#             lname = l.get("name", "").lower()
#             for tok in tokens:
#                 if tok.lower() in lname:
#                     return l.get("id")
#         return None

#     def create_card_on_list(
#         self, key: str, token: str, list_id: str, card_name: str, desc: Optional[str] = None, pos: str = "top"
#     ) -> Dict[str, Any]:
#         """
#         Create a Trello card in the specified list.
#         Returns the created card JSON.
#         """
#         if not list_id:
#             raise ValueError("list_id is required")
#         if not card_name or not card_name.strip():
#             raise ValueError("card_name must be provided")
#         payload = {"idList": list_id, "name": card_name.strip(), "pos": pos}
#         if desc:
#             payload["desc"] = desc
#         return self._trello_post("/cards", key, token, data=payload)

#     def create_card_from_query(
#         self,
#         query: str,
#         key: str,
#         token: str,
#         workspace_input: str,
#         include_closed: bool = False,
#         pos: str = "top",
#         fallback_card_name: Optional[str] = None,
#     ) -> Dict[str, Any]:
#         """
#         Main helper:
#           - Parse query to extract board/list/card names
#           - Resolve board -> board_id
#           - Resolve list -> list_id (fetch lists on board and match)
#           - Create the card in that list
#         Returns created card JSON on success or raises ValueError on failure.
#         """
#         parsed = self._extract_board_list_card_from_query(query)
#         board_name = (parsed.get("board") or "").strip()
#         list_name = (parsed.get("list") or "").strip()
#         card_name = (parsed.get("card") or "").strip()

#         if not card_name:
#             if fallback_card_name:
#                 card_name = fallback_card_name.strip()
#             else:
#                 raise ValueError("Could not extract card name from query and no fallback provided.")

#         # 1) resolve board
#         board_map = self.fetch_workspace_board_map(key, token, workspace_input, include_closed=include_closed)
#         board_id = None
#         resolved_board_name = None
#         if board_name:
#             # exact then case-insensitive
#             if board_name in board_map:
#                 board_id = board_map[board_name]
#                 resolved_board_name = board_name
#             else:
#                 lower_map = {k.lower(): v for k, v in board_map.items()}
#                 board_id = lower_map.get(board_name.lower())
#                 if board_id:
#                     # find how the board was actually named (preserve case)
#                     for k, v in board_map.items():
#                         if v == board_id:
#                             resolved_board_name = k
#                             break

#         # fallback: try to find board by tokens in query if board not extracted or not found
#         if not board_id:
#             qtokens = [t.strip() for t in re.split(r"[,\s]+", query) if len(t.strip()) > 2]
#             candidates = []
#             for name, bid in board_map.items():
#                 lname = name.lower()
#                 for tok in qtokens:
#                     if tok.lower() in lname:
#                         candidates.append((name, bid))
#                         break
#             if len(candidates) == 1:
#                 resolved_board_name, board_id = candidates[0]
#             elif len(candidates) > 1:
#                 chosen = None
#                 for name, bid in candidates:
#                     for tok in qtokens:
#                         if name.lower().startswith(tok.lower()):
#                             chosen = (name, bid)
#                             break
#                     if chosen:
#                         break
#                 if chosen:
#                     resolved_board_name, board_id = chosen

#         if not board_id:
#             raise ValueError(
#                 f"Could not determine target board from query '{query}'. Extracted board: '{board_name}'. Available boards: {list(board_map.keys())}"
#             )

#         # 2) fetch lists on the resolved board and find list id
#         lists = self.get_lists_on_board(key, token, board_id, include_closed=include_closed)
#         list_id = None
#         if list_name:
#             list_id = self.find_list_id_by_name(lists, list_name)
#         if not list_id:
#             # try fuzzy search using tokens from query (similar to earlier)
#             qtokens = [t.strip() for t in re.split(r"[,\s]+", query) if len(t.strip()) > 2]
#             candidates = []
#             for l in lists:
#                 lname = l.get("name", "").lower()
#                 for tok in qtokens:
#                     if tok.lower() in lname:
#                         candidates.append((l.get("name"), l.get("id")))
#                         break
#             if len(candidates) == 1:
#                 list_id = candidates[0][1]
#                 list_name = candidates[0][0]
#             elif len(candidates) > 1:
#                 chosen = None
#                 for lname, lid in candidates:
#                     for tok in qtokens:
#                         if lname.lower().startswith(tok.lower()):
#                             chosen = (lname, lid)
#                             break
#                     if chosen:
#                         break
#                 if chosen:
#                     list_name, list_id = chosen

#         if not list_id:
#             available_lists = [l.get("name") for l in lists]
#             raise ValueError(
#                 f"Could not find target list for query '{query}'. Extracted list: '{list_name}'. Available lists on board '{resolved_board_name}': {available_lists}"
#             )

#         # 3) create the card
#         created_card = self.create_card_on_list(key, token, list_id, card_name, desc=None, pos=pos)
#         return created_card


# if __name__ == "__main__":

# Demo / example runs for the three main features:
# 1) create_board_from_query (uses Composio toolset + LLM)
# 2) create_list_from_query (LLM extraction -> resolve board in workspace -> create list via Trello API)
# 3) create_card_from_query (LLM extraction -> resolve board/list -> create card via Trello API)


    # trello_agent = TRELLO(api_key=composio_api_key)
    # WORKSPACE_LINK = "https://trello.com/w/userworkspace57275986/home"


    # try:
    #     print("\n=== Example A: create_board_from_query ===")
    #     create_board_query = "Please add a board named as Naman's Workspace"
    #     board_result = trello_agent.create_board_from_query(create_board_query)
    #     print("create_board_from_query returned:", board_result)
    # except Exception as e:
    #     print("Error while creating board:", e)

    # try:
    #     print("\n=== Example B: create_list_from_query ===")

    #     list_query = "Please add a list named as Kaam ki cheez to Naman's Workspace"
    #     created_list = trello_agent.create_list_from_query(
    #     list_query,
    #     KEY,
    #     TOKEN,
    #     WORKSPACE_LINK,
    #     include_closed=False,
    #     pos="top",
    #     fallback_list_name="List",
    #     )
    #     print("Created list:", created_list.get("name"), "id:", created_list.get("id"))
    # except Exception as e:
    #     print("List creation error:", e)



    # try:
    #     print("\n=== Example C: create_card_from_query ===")

    #     card_query = "Please add a card named as Gaanja to the list named as Kaam ki cheez in  Naman's Workspace  "
    #     created_card = trello_agent.create_card_from_query(
    #     card_query,
    #     KEY,
    #     TOKEN,
    #     WORKSPACE_LINK,
    #     include_closed=False,
    #     pos="top",
    #     fallback_card_name="lunch",
    #     )
    #     print("Created card:", created_card.get("name"), "id:", created_card.get("id"))
    # except Exception as e:
    #     print("Card creation error:", e)


    # print("\nDemo finished. If any of the example queries failed, adjust the query text to match exact board/list names in your workspace or provide fallbacks.")