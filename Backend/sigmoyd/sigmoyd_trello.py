


# sigmoyd_trello.py
"""
Lightweight, robust Composio/Trello read-ops helper with LLM integration.

Key points:
- No hard-coded API keys. Read from env or pass keys explicitly.
- Lazily initializes ComposioToolSet and LLM.
- Provides async methods for:
  - get_list_content
  - get_deadline
  - get_all_deadlines
  - get_checklist
  - get_all_actions (board snapshot)
- Uses logging instead of prints. Good for production & debugging.
"""

from __future__ import annotations
import os
import re
import json
import sys
import logging
import ast
from pathlib import Path
from typing import Any, Dict, Optional, List
from datetime import datetime, timedelta
import pytz

# Optional zoneinfo
try:
    from zoneinfo import ZoneInfo
    HAVE_ZONEINFO = True
except Exception:
    HAVE_ZONEINFO = False

# LLM (Google Gemini) client
try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except Exception:
    ChatGoogleGenerativeAI = None  # will raise if used without package

# Try composio imports with reasonable fallbacks
ComposioToolSet = None
try:
    from composio.tools.toolset import ComposioToolSet  # primary
except Exception:
    try:
        from composio import ComposioToolSet  # secondary
    except Exception:
        try:
            from composio_langchain import ComposioToolSet  # tertiary
        except Exception:
            # Allow runtime error later when toolset is actually needed
            ComposioToolSet = None

# Composio exception fallback
try:
    from composio.client.exceptions import NoItemsFound
except Exception:
    class NoItemsFound(Exception):
        pass

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Config from environment (prefer to pass keys explicitly to functions instead)
COMPOSIO_API_KEY = os.environ.get("COMPOSIO_API_KEY")
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY")
DEFAULT_TIMEZONE = "Asia/Kolkata"


def get_llm(gemini_api_key: Optional[str] = None):
    """Return an LLM client (synchronous invoke style used in original code)."""
    key = (gemini_api_key or GEMINI_API_KEY)
    if not key:
        return None
    if ChatGoogleGenerativeAI is None:
        raise RuntimeError("langchain_google_genai.ChatGoogleGenerativeAI not available")
    return ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=key)


def _iso_to_aware(dt_str: Optional[str], tz_name: str = DEFAULT_TIMEZONE) -> Optional[datetime]:
    if not dt_str:
        return None
    s = dt_str
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(s)
    except Exception:
        # common fallback
        try:
            dt = datetime.strptime(dt_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
            # assume UTC
            if HAVE_ZONEINFO:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            else:
                dt = pytz.UTC.localize(dt)
        except Exception:
            return None
    # convert to requested tz
    try:
        if HAVE_ZONEINFO:
            tz = ZoneInfo(tz_name)
        else:
            tz = pytz.timezone(tz_name)
        if dt.tzinfo is None:
            # assume UTC if naive
            if HAVE_ZONEINFO:
                dt = dt.replace(tzinfo=ZoneInfo("UTC"))
            else:
                dt = pytz.UTC.localize(dt)
        return dt.astimezone(tz)
    except Exception:
        return dt


class SigmoydTrello:
    """Encapsulate Composio toolset and LLM operations for read-only Trello helpers."""

    def __init__(self, composio_api_key: Optional[str] = None, gemini_api_key: Optional[str] = None):
        self.composio_api_key = composio_api_key or COMPOSIO_API_KEY
        self.gemini_api_key = gemini_api_key or GEMINI_API_KEY
        self._toolset = None
        self._llm = None

        if not self.composio_api_key:
            logger.warning("COMPOSIO_API_KEY not provided. API calls will fail until provided.")
        if not self.gemini_api_key:
            logger.info("GEMINI_API_KEY not provided; LLM calls will be skipped where optional.")

    @property
    def llm(self):
        if self._llm is None and self.gemini_api_key:
            self._llm = get_llm(self.gemini_api_key)
        return self._llm

    @property
    def toolset(self):
        if self._toolset is None:
            if ComposioToolSet is None:
                raise RuntimeError("ComposioToolSet not importable. Install the composio SDK or provide a local path.")
            if not self.composio_api_key:
                raise RuntimeError("Composio API key required to initialize toolset.")
            self._toolset = ComposioToolSet(api_key=self.composio_api_key)
        return self._toolset

    def _exec_action(self, action: str, params: Dict[str, Any]):
        """Wrapper to call toolset.execute_action safely and return raw response."""
        try:
            return self.toolset.execute_action(params=params, action=action)
        except Exception as e:
            logger.warning("Composio action %s failed: %s", action, e)
            return None

    async def get_task_functions(self, query: str) -> List[str]:
        """
        Ask LLM which function(s) should run for a query.
        Returns an ordered list of function names (strings).
        """
        if not self.llm:
            raise RuntimeError("LLM not available")
        prompt = f"""
        Decide which of these functions best match the user query (return a Python list literal e.g. ["get_list_content"]):
        functions = ["get_card_description","get_list_content","get_deadline","get_all_deadlines","get_board_content","get_card_comment","get_all_actions","get_checklist"]
        Query: {query}
        Return only the list.
        """
        resp = self.llm.invoke(prompt)
        txt = (resp.content or "").strip()
        try:
            parsed = ast.literal_eval(txt)
            if isinstance(parsed, (list, tuple)):
                return [str(p) for p in parsed]
        except Exception:
            # fallback: detect function names by substring (preserves order in prompt)
            out = []
            lower = txt.lower()
            for fn in ["get_card_description","get_list_content","get_deadline","get_all_deadlines","get_board_content","get_card_comment","get_all_actions","get_checklist"]:
                if fn.lower() in lower:
                    out.append(fn)
            return out
        return []

    async def get_board_id(self, query: str) -> Optional[str]:
        """Extract Board ID from user query using a quick regex or LLM fallback."""
        # quick regex
        m = re.search(r'(?:board[_\s-]*id|bid)\s*[:=]?\s*([A-Za-z0-9_\-:.]{4,})', query, flags=re.IGNORECASE)
        if m:
            return m.group(1)
        # try the LLM if available
        if self.llm:
            prompt = f"Extract Board_ID from the query below and return only the id.\nQuery: {query}"
            try:
                resp = self.llm.invoke(prompt)
                out = (resp.content or "").strip()
                # simple heuristics to pull id
                m2 = re.search(r'([A-Za-z0-9_\-:.]{4,})', out)
                if m2:
                    return m2.group(1)
                return out or None
            except Exception:
                return None
        return None

    async def get_list_content(self, idBoard: str, query: str) -> Dict[str, Any]:
        """
        Get all card names (and simple descriptions) for a list whose name is extracted from `query`.
        """
        if not idBoard:
            return {"status": "error", "reason": "idBoard required"}
        # try to extract list name via LLM (if available) else attempt heuristics
        list_name = None
        if self.llm:
            p = f"Extract only the list name from this query (no extra text): {query}"
            try:
                list_name = (self.llm.invoke(p).content or "").strip()
            except Exception:
                list_name = None
        if not list_name:
            # heuristics: look for 'list <name>' or quoted text
            m = re.search(r"(?:list|List)\s+['\"]?([^'\"\n,]+)['\"]?", query)
            if m:
                list_name = m.group(1).strip()

        # fetch lists for board
        resp = self._exec_action("TRELLO_GET_BOARDS_LISTS_BY_ID_BOARD", {"idBoard": idBoard})
        if not resp:
            return {"status": "error", "reason": "Failed to fetch lists"}
        lists = []
        try:
            data = resp.get("data", {}) if isinstance(resp, dict) else resp
            lists = data.get("details") if isinstance(data, dict) and "details" in data else (data.get("lists") or data)
            if not isinstance(lists, list):
                lists = [lists]
        except Exception:
            lists = []

        # map name->id
        name_to_id = {}
        for lst in lists:
            if isinstance(lst, dict):
                name = lst.get("name", "")
                lid = lst.get("id")
                if name and lid:
                    name_to_id[name] = lid

        # attempt to find a match (exact, case-insensitive, contains)
        list_id = None
        matched_name = None
        if list_name and list_name in name_to_id:
            list_id = name_to_id[list_name]; matched_name = list_name
        else:
            lower_map = {k.lower(): k for k in name_to_id}
            if list_name and list_name.lower() in lower_map:
                matched_name = lower_map[list_name.lower()]; list_id = name_to_id[matched_name]
            else:
                # try substring match
                for k in name_to_id:
                    if list_name and (list_name.lower() in k.lower() or k.lower() in list_name.lower()):
                        matched_name = k; list_id = name_to_id[k]; break

        if not list_id:
            return {"status": "not_found", "available_lists": list(name_to_id.keys()), "extracted_name": list_name}

        # fetch cards for list
        cards_resp = self._exec_action("TRELLO_GET_LISTS_CARDS_BY_ID_LIST", {"idList": list_id})
        cards = []
        try:
            if isinstance(cards_resp, dict):
                cdata = cards_resp.get("data", {}) if "data" in cards_resp else cards_resp
                cards = cdata.get("details") if isinstance(cdata, dict) and "details" in cdata else (cdata.get("cards") or cdata)
            elif isinstance(cards_resp, list):
                cards = cards_resp
            if not isinstance(cards, list):
                cards = [cards]
        except Exception:
            cards = []

        tasks = []
        for c in cards:
            if not isinstance(c, dict):
                continue
            # try to gather checklist items first if directly present
            if "checkItems" in c and isinstance(c["checkItems"], list):
                tasks.extend([it.get("name") for it in c["checkItems"] if isinstance(it, dict) and it.get("name")])
                continue
            # otherwise attempt to fetch checklists per card
            cid = c.get("id")
            if not cid:
                continue
            # try to see if card has checklists embedded
            try:
                chk_resp = self._exec_action("TRELLO_GET_CARDS_CHECKLISTS_BY_ID_CARD", {"idCard": cid})
                items = []
                if isinstance(chk_resp, list):
                    for chk in chk_resp:
                        if isinstance(chk, dict):
                            for it in (chk.get("checkItems") or chk.get("items") or []):
                                if isinstance(it, dict) and it.get("name"):
                                    items.append(it["name"])
                elif isinstance(chk_resp, dict):
                    data = chk_resp.get("data") or chk_resp
                    cand = data.get("details") or data.get("checklists") or data
                    if isinstance(cand, list):
                        for chk in cand:
                            if isinstance(chk, dict):
                                for it in (chk.get("checkItems") or chk.get("items") or []):
                                    if isinstance(it, dict) and it.get("name"):
                                        items.append(it["name"])
                if items:
                    tasks.extend(items)
            except Exception:
                continue

        return {"status": "success", "list_name": matched_name or list_name, "list_id": list_id, "tasks": tasks, "total_tasks": len(tasks)}

    async def get_deadline(self, idBoard: str, query: str) -> Optional[str]:
        """Return a human-friendly summary for matching card name deadlines (uses LLM optionally)."""
        if not idBoard:
            return None
        # extract card name
        card_name = None
        if self.llm:
            try:
                resp = self.llm.invoke(f"Extract only the card name from: {query}")
                card_name = (resp.content or "").strip()
            except Exception:
                card_name = None
        if not card_name:
            m = re.search(r'card\s+["\']?([^"\']+)["\']?', query, flags=re.IGNORECASE)
            if m:
                card_name = m.group(1).strip()
        if not card_name:
            return None

        # fetch all cards on board
        cards_resp = self._exec_action("TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD", {"idBoard": idBoard})
        cards = []
        try:
            if isinstance(cards_resp, dict):
                data = cards_resp.get("data") or cards_resp
                cards = data.get("details") or data.get("items") or data
            elif isinstance(cards_resp, list):
                cards = cards_resp
            if not isinstance(cards, list):
                cards = [cards]
        except Exception:
            cards = []

        # timezone now
        if HAVE_ZONEINFO:
            now = datetime.now(ZoneInfo(DEFAULT_TIMEZONE))
        else:
            now = datetime.now(pytz.timezone(DEFAULT_TIMEZONE))

        matches = []
        for c in cards:
            if not isinstance(c, dict):
                continue
            name = c.get("name", "")
            if not name:
                continue
            if card_name.lower() in name.lower() or name.lower() == card_name.lower():
                due_raw = c.get("due")
                due_ist = _iso_to_aware(due_raw)
                time_left = (due_ist - now) if due_ist else None
                matches.append({
                    "id": c.get("id"),
                    "card_name": name,
                    "deadline_ist": due_ist.isoformat() if due_ist else None,
                    "time_left": time_left
                })
        if not matches:
            return f"No matches for '{card_name}' on board {idBoard}."

        # format result; optionally ask LLM to produce friendly summary
        def fmt_timedelta(td: Optional[timedelta]) -> str:
            if td is None:
                return "No deadline assigned"
            total = int(td.total_seconds())
            sign = "-" if total < 0 else ""
            total = abs(total)
            d, r = divmod(total, 86400)
            h, r = divmod(r, 3600)
            m, s = divmod(r, 60)
            parts = []
            if d: parts.append(f"{d}d")
            if h: parts.append(f"{h}h")
            if m: parts.append(f"{m}m")
            if not parts: parts.append(f"{s}s")
            return sign + " ".join(parts)

        matches_sorted = sorted(matches, key=lambda x: x["time_left"] if x["time_left"] is not None else timedelta.max)
        lines = []
        for m in matches_sorted:
            lines.append(f"Card: {m['card_name']}, Deadline(IST): {m['deadline_ist'] or 'No deadline'}, Time Left: {fmt_timedelta(m['time_left'])}")

        block = "\n".join(lines)
        if self.llm:
            prompt = f"Summarize these deadlines and make them human-friendly:\n{block}\nReturn a short bullet list."
            try:
                resp = self.llm.invoke(prompt)
                return (resp.content or "").strip()
            except Exception:
                return block
        return block

    async def get_all_deadlines(self, idBoard: str, query: str) -> Optional[str]:
        """Return a sorted, human-friendly summary of all deadlines on a board (LLM-enhanced if available)."""
        if not idBoard:
            return None
        resp = self._exec_action("TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD", {"idBoard": idBoard})
        cards = []
        try:
            if isinstance(resp, dict):
                data = resp.get("data") or resp
                cards = data.get("details") or data.get("items") or data
            elif isinstance(resp, list):
                cards = resp
            if not isinstance(cards, list):
                cards = [cards]
        except Exception:
            cards = []

        if HAVE_ZONEINFO:
            now = datetime.now(ZoneInfo(DEFAULT_TIMEZONE))
        else:
            now = datetime.now(pytz.timezone(DEFAULT_TIMEZONE))

        matches = []
        for c in cards:
            if not isinstance(c, dict):
                continue
            due_raw = c.get("due")
            due_ist = _iso_to_aware(due_raw)
            if due_ist:
                matches.append({
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "deadline_ist": due_ist.isoformat(),
                    "time_left": (due_ist - now)
                })
        if not matches:
            return "No deadlines found on this board."

        matches_sorted = sorted(matches, key=lambda x: x["time_left"] if x["time_left"] is not None else timedelta.max)
        lines = []
        for m in matches_sorted:
            tl = m["time_left"]
            days = getattr(tl, "days", None)
            lines.append(f"Card: {m['name']}, Deadline(IST): {m['deadline_ist']}, Time Left: {tl}")

        block = "\n".join(lines)
        if self.llm:
            try:
                resp = self.llm.invoke(f"Summarize these deadlines:\n{block}\nReturn short bullet list.")
                return (resp.content or "").strip()
            except Exception:
                return block
        return block

    async def get_checklist(self, idBoard: str, query: str) -> Dict[str, Any]:
        """
        Fetch checklists for a board and return structured results + LLM summary (if available).
        Returns dict {"results": {card_id: {...}}, "llm_summary": str|None}
        """
        if not idBoard:
            return {"status": "error", "reason": "idBoard required", "results": {}, "llm_summary": None}
        raw = self._exec_action("TRELLO_GET_BOARDS_CHECKLISTS_BY_ID_BOARD", {"idBoard": idBoard})
        # Attempt to parse varied shapes into list of checklist dicts
        checklists = []
        try:
            if isinstance(raw, dict):
                data = raw.get("data") or raw
                if isinstance(data, dict) and "details" in data:
                    checklists = data.get("details") or []
                elif isinstance(data, list):
                    checklists = data
                elif "checklists" in data:
                    checklists = data.get("checklists") or []
            elif isinstance(raw, list):
                checklists = raw
            else:
                # plain text fallback - return as summary
                if isinstance(raw, str):
                    if self.llm:
                        try:
                            summary = self.llm.invoke(f"Summarize these checklists text:\n{raw}")
                            return {"results": {}, "llm_summary": (summary.content or "").strip()}
                        except Exception:
                            return {"results": {}, "llm_summary": raw}
        except Exception:
            checklists = []

        results = {}
        for chk in (checklists or []):
            if not isinstance(chk, dict):
                continue
            cid = chk.get("idCard") or chk.get("cardId")
            items = chk.get("checkItems") or chk.get("items") or []
            normalized_items = []
            if isinstance(items, list):
                for it in items:
                    if isinstance(it, dict):
                        normalized_items.append({
                            "item_id": it.get("id") or it.get("idChecklist") or None,
                            "text": it.get("name") or it.get("text") or None,
                            "state": it.get("state") or None
                        })
            results.setdefault(cid or "<unknown_card>", {"card_name": None, "deadline": None, "tasks": []})
            results[cid or "<unknown_card>"]["tasks"].extend(normalized_items)

        # enrich with card name & deadline if possible
        try:
            cards_resp = self._exec_action("TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD", {"idBoard": idBoard})
            cards = []
            if isinstance(cards_resp, dict):
                data = cards_resp.get("data") or cards_resp
                cards = data.get("details") or data.get("items") or data
            elif isinstance(cards_resp, list):
                cards = cards_resp
            if not isinstance(cards, list):
                cards = [cards]
            card_map = {c.get("id"): c for c in cards if isinstance(c, dict) and c.get("id")}
            for cid, entry in list(results.items()):
                if cid in card_map:
                    entry["card_name"] = card_map[cid].get("name")
                    entry["deadline"] = card_map[cid].get("due")
        except Exception:
            pass

        # LLM summary
        llm_summary = None
        if self.llm:
            try:
                block_lines = []
                for cid, info in results.items():
                    card_name = info.get("card_name") or cid
                    block_lines.append(f"Card: {card_name} (ID: {cid})")
                    for t in info.get("tasks", []):
                        block_lines.append(f"  - {t.get('text')} (state: {t.get('state')})")
                block = "\n".join(block_lines)[:2000]
                resp = self.llm.invoke(f"Summarize these checklist items for user:\n{block}\nReturn a short list.")
                llm_summary = (resp.content or "").strip()
            except Exception:
                llm_summary = None

        return {"status": "success", "results": results, "llm_summary": llm_summary}

    async def get_all_actions(self, idBoard: str) -> str:
        """
        Produce a human readable snapshot of the board: lists, cards, descriptions, deadlines, members.
        Returns a plain text snapshot (LLMless).
        """
        if not idBoard:
            raise ValueError("idBoard required")

        # fetch lists
        lists_resp = self._exec_action("TRELLO_GET_BOARDS_LISTS_BY_ID_BOARD", {"idBoard": idBoard}) or {}
        lists = []
        try:
            data = lists_resp.get("data") or lists_resp
            lists = data.get("details") or data.get("lists") or data
            if not isinstance(lists, list):
                lists = [lists]
        except Exception:
            lists = []

        # fetch all cards as fallback
        cards_resp = self._exec_action("TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD", {"idBoard": idBoard}) or {}
        cards = []
        try:
            data = cards_resp.get("data") or cards_resp
            cards = data.get("details") or data.get("items") or data
            if not isinstance(cards, list):
                cards = [cards]
        except Exception:
            cards = []

        # build map: list_id -> cards
        by_list = {}
        for c in cards:
            if not isinstance(c, dict):
                continue
            lid = c.get("idList") or c.get("listID") or "<no-list>"
            by_list.setdefault(lid, []).append(c)

        # format snapshot
        lines = []
        board_name = None
        # try to extract board name from lists_resp
        try:
            if isinstance(lists_resp, dict):
                board = (lists_resp.get("data") or {}).get("board") or lists_resp.get("board")
                if isinstance(board, dict):
                    board_name = board.get("name")
                elif isinstance(board, str):
                    board_name = board
        except Exception:
            board_name = None

        lines.append(f"Board: {board_name or '<unnamed>'} (ID: {idBoard})")
        lines.append("")
        lines.append("Lists & Cards:")
        for lst in lists:
            if not isinstance(lst, dict):
                continue
            lid = lst.get("id")
            lname = lst.get("name") or "<unnamed list>"
            lines.append(f"- {lname} (List ID: `{lid}`)")
            card_list = by_list.get(lid) or []
            if not card_list:
                lines.append("    - (no cards)")
                continue
            for c in card_list:
                cid = c.get("id")
                cname = c.get("name") or "<unnamed card>"
                desc = (c.get("desc") or "")[:300]
                due = c.get("due") or c.get("deadline") or "<none>"
                lines.append(f"    - Card: {cname} (ID: `{cid}`)")
                lines.append(f"        - Description: {desc if desc else '<none>'}")
                lines.append(f"        - Deadline: {due}")
            lines.append("")

        return "\n".join(lines)


# Minimal example usage (only runs when executed directly)
if __name__ == "__main__":
    import asyncio
    logging.getLogger().setLevel(logging.DEBUG)
    api_key = os.environ.get("COMPOSIO_API_KEY")
    gemini = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        logger.warning("COMPOSIO_API_KEY not set. Example will not run Composio calls.")
    s = SigmoydTrello(composio_api_key=api_key, gemini_api_key=gemini)
    async def demo():
        # small demo - does not call Composio if no key
        try:
            bid = "your-board-id-here"
            out = await s.get_all_actions(bid)
            print(out)
        except Exception as e:
            logger.error("Demo failed: %s", e)
    asyncio.run(demo())











# iske niche uncomment karo 
# import os
# import re
# import json
# import sys
# from pathlib import Path
# from typing import Any, Dict, Optional, List, Tuple
# import asyncio
# import ast                    
# from langchain_google_genai import ChatGoogleGenerativeAI
# from datetime import datetime, timedelta
# import pytz
# import inspect

# # Try to import ComposioToolSet with fallback options
# ComposioToolSet = None
# Action = None

# # Add Composio path if it exists (for local development)
# backend_dir = Path(__file__).parent.parent
# composio_path = backend_dir / "composio" / "python"
# if not composio_path.exists():
#     composio_path = backend_dir.parent / "Model" / "composio" / "python"

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
#                     if 'sigmoyd_trello' not in module_name:
#                         removed_modules[module_name] = sys.modules[module_name]
#                         del sys.modules[module_name]
                
#                 try:
#                     from plugins.langchain.composio_langchain.toolset import ComposioToolSet
#                 except ImportError:
#                     # Restore modules if import failed
#                     for module_name, module_obj in removed_modules.items():
#                         sys.modules[module_name] = module_obj

# # Try to import Action (may not be available in all versions)
# try:
#     from composio import Action
# except ImportError:
#     try:
#         from composio_langchain import Action
#     except ImportError:
#         # Action is optional, can be None
#         Action = None

# # zoneinfo fallback
# try:
#     from zoneinfo import ZoneInfo  # Python 3.9+
#     HAVE_ZONEINFO = True
# except Exception:
#     HAVE_ZONEINFO = False

# # ------------ Config ----------
# composio_api_key = os.environ.get("COMPOSIO_API_KEY", "ak_MpJHqcANBArbbIx2uQdH")
# gemini_api_key = os.environ.get("GEMINI_API_KEY")
# composio_workspace_url = os.environ.get("COMPOSIO_WORKSPACE_URL", "").strip()

# # Initialize LLM (optional) - will be reinitialized in process_query if needed
# llm = None

# def get_llm(gemini_api_key_param: str = None):
#     """Get or create LLM instance with provided API key"""
#     global llm
#     actual_key = gemini_api_key_param or gemini_api_key
#     if actual_key:
#         try:
#             return ChatGoogleGenerativeAI(model="gemini-robotics-er-1.5-preview", api_key=actual_key)
#         except Exception:
#             return None
#     return llm

# async def get_all_actions(query: str, llm_instance=None):
#     task=f'''You are an input classifier expert. i.e on reading the input you can classify the query into 3 classes of tasks, namely 
#     1. Read Operation : The query asks you to read some details from the Trello board, it may be the deadline of a task, maybe a pending tasks from the list, maybe the details of the board, list or card
#     2. Write Operation: The query asks you to update the details of maybe a Trello board, list, card, or add some more details in the card, maybe a comment, description, or maybe add some lists in the board, or cards into the list etc.
#     3. Delete Operation: The query asks you delete some content from the Trello Board, it maybe the whole Trello Board, a list, a card, description of the card etc

#     So I want you to use the query: {query} and output only the name of the operation ,there can be multiple options in a query like Read and Write operations combined or Read, Write and Delete operations so
#     make a list of all such operations extracted and give as output in INORDER. ORDER IS IMPORTANT.

#     example_query: I wanna update the description of a card named Taran in Bakshish's Workspace. 
#     result: [Write Operation]

#     example_query: I wanna delete the card X.
#     result: [Delete Operation]

#     example_query: Fetch all the list content from the board uddgbfwf.
#     result: [Read Operation]

#     NOTHING MORE IS NEEDED.
#     '''

#     llm_to_use = llm_instance or llm
#     if not llm_to_use:
#         raise RuntimeError("LLM not initialized. Please provide gemini_api_key.")
#     response = llm_to_use.invoke(task)
#     return response.content

# class ReadOperation: 
#     def __init__(self, composio_api_key: str, llm_instance=None):
#         if not composio_api_key:
#             raise RuntimeError("COMPOSIO_API_KEY is required")
#         self.toolset = ComposioToolSet(api_key=composio_api_key)
#         try:
#             self.tools = self.toolset.get_tools() or []
#         except Exception as e:
#             print("Warning: error fetching tools at init:", e)
#             self.tools = []
#         print(f"[DEBUG] Cached {len(self.tools)} composio tools at init.")
#         # Use provided LLM instance or fall back to global
#         self.llm = llm_instance or llm
    
#     async def get_task(self, query: str):
#         task_prompt = f""" You are a Trello task classifier expert and your main aim is to extract the task that is given in the query: {query}. 
#         The task could be anything related to reading, fetching data from cards, lists and boards. I want you to classify the tasks 
#         from the function array below: 
#         function array: ["get_card_description", "get_list_content", "get_deadline","get_board_content", "get_card_comment"]
        
#         the functionality of the following functions mapped with the array are as follows:
#         function: get_card_description --> functionality: fetches the description of the card who's name is provided in the query. Query provides with the boardID and cardName. Example of queries can be:[
#         1) Fetch me the card descriptipon of Taran's card from board id: abcxdeejwd
#         2) Please tell me the context of the card whose name is Bakshish on board who;s id is : abcderf
#         ]


#         function: get_list_content --> functionality: fetches the number of cards first and then content of each card including their descriptions with title. Use the list name provided in the query for finding out the on which list we have to perform actions
#         Required Parameters: idBoard, List Name
#         Some example of possible queries are:
#         [
#         “Show me all the cards in To Dollist along with their descriptions of board id: sjdghWADGB.”
#         “How many cards are in the In Progress list OF BOARD who's id is ajhdDBEEBDF? Also give me their details.”
#         “Fetch the contents of the list Done in my workspace with bid:hdvQWDVDB, including the card titles and descriptions.”
#         ]

#         function: get_deadline --> functionality: fetches the deadline assigned to a specific card and give as the output as deadline of the respective card. Use the card name provided in the query
#         Required Parameters: idBoard, Card Name
#         Some example of possible queries are:
#         [
#         “What's the deadline for the card Finalize Report? with board ID: 12345”
#         “Tell me the due date of Bug Fix #123 card of bid: svuQWADVqwbd.”
#         “When does the Presentation Draft card which belongs to Board who;s id is dbQDBDB need to be completed?”
#         ]

#         function: get_all_deadlines --> functionality: fetches all the deadlines of a particular board whose ID is provided in the query.This function uses the board ID as a parameter and is used to fetch all the deadlines of all the cards present in a particular board.
#         Required Parameters: idBoard
#         Some example of possible queries are:
#         [
#         “Show me all the deadlines for the board whose identity is SJBDbndadC.”
#         “List every card and its due date from board ID 12345.”
#         “What are the upcoming deadlines in the Marketing Campaign board with Board ID: AVBDaehbdkeABD?”    
#         ]

#         function: get_all_actions --> functionality: fetches all the board content, all the lists, all the cards inside each list and give as the output as the whole context of the whole board. Use the name of the board name/ board ID mentioned in the query.
#         Required Parameters: idBoard
#         Some examples of possible queries are:
#         [
#         Tell me what's present in the board who's id is sjdbbdbd.
#         what's there in bid:ashddacbc
#         Give mne
#         ]


#         function: get_card_comment --> functionality: fetches all the comments in a particular card which is in a list which is a particular baord. Use the query to use card name, list name and board_name/board_id to reach till trhe comments section of a particlar card.
        
#         Some example of possible queries are:
#         [
#         “Show me all the comments on the card UI Fixes in the In Progress list of the board with ID board_9876.”
#         “Fetch comments for the Testing Phase card under the QA list in the board with ID board_1122.”
#         “What feedback is on the Logo Design card in the Design list of the board with ID board_5544?”
#         ]

#         function: get_checklist --> functionality: fetches all the tasks in a board who's board ID is mentioned in the query. Uses the board Id and the Query as the parameter.
#         Some example of possible queries are:
#         [
#         Fetch me all the pending tasks from the board who;s is id : kdnJDBKBJD
#         Whats tasks remain for the day?
#         What more to do?
#         How much percentage of work is pending?
#         How much percentage of work needs to be done?
#         How much percentage of work needs to be complete?
#         etc..
#         ]

#         Using the above functions and functionalities, I want youto decide the most accurate functionality that my query: {query} wants to perform. Always return a list of functions that needs to be performed 
#         taking the above query as reference. Return a list only containing the function names only. NOTHING MORE IS NEEDED
#         """

#         llm_to_use = self.llm or llm
#         if not llm_to_use:
#             raise RuntimeError("LLM not initialized. Please provide gemini_api_key.")
#         response = llm_to_use.invoke(task_prompt)
#         # <-- minimal change: return content (string)
#         return response.content
    
#     async def get_board_id(self, query: str):
#         task = f"""You are a board information extractor expert, your main task is to extract the board_id (whatever is mentioned in the query) from the query: {query}
#         You only return the Board_ID, in the format given below (JSON or plain text is fine):
#         Board_ID: idBoard

#         Example: Query: Extract the Board's content who's id is abcde.
#         Output: Board_ID: abcde
#         """

#         llm_to_use = self.llm or llm
#         if not llm_to_use:
#             raise RuntimeError("LLM not initialized. Please provide gemini_api_key.")
#         result = llm_to_use.invoke(task)
#         output = (result.content or "").strip()
#         try:
#             parsed = json.loads(output)
#             bid = parsed.get("Board_ID") or parsed.get("board_id") or parsed.get("BoardId")
#             if bid:
#                 return bid
#         except Exception:
#             pass
#         m = re.search(r'Board[_\s-]*ID\s*[:=]\s*(["\']?)([A-Za-z0-9_\-:.]+)\1', output, flags=re.IGNORECASE)
#         if m:
#             return m.group(2).strip()
#         m2 = re.search(r'\b(?:board[_\s-]*id|id)\b\s*[:=]\s*(["\']?)([A-Za-z0-9_\-:.]+)\1', output, flags=re.IGNORECASE)
#         if m2:
#             return m2.group(2).strip()
        
#         return output

#     async def get_list_content(self, idBoard: str, query: str):
#         """
#         1) Use the LLM to extract the target list name from `query`.
#         2) Fetch all lists for `idBoard` and build a name->id map.
#         3) If extracted name is found, fetch cards for that list and extract
#         name/description/deadline for each card.
#         4) Save the cards to `list_<list_id>_cards.json`.
#         5) Call the LLM to get a summary of the list (cards + meta) and return result.

#         Returns a dict with keys:
#         - status: "success" | "not_found" | "error"
#         - list_name, list_id, cards (list of dicts), summary (LLM text), file_path
#         - or error information
#         """
#         # 0) prepare Composio toolset
#         toolset = self.toolset

#         # 1) Ask the LLM to extract the list name from the user query
#         task = f"""
#         You are a list name extractor expert, that is your main aim is to extract the name of the list from the query
#         provided by the user. You just extract the name of the list nothing more.

#         Example 1: I wanna fetch content of a list named Taran from Sigmoyd's workspace
#         Expected Output: Taran

#         Example 2: I wanna fetch the whole list content of Sigmoyd's List from the board_id jbdfiebdfwibf.
#         Expected Output: Sigmoyd's List

#         User query: {query}

#         Respond with only the list name (no extra words).
#     """
#         # llm.invoke is assumed available and returns an object with `content`
#         llm_to_use = self.llm or llm
#         if not llm_to_use:
#             raise RuntimeError("LLM not initialized. Please provide gemini_api_key.")
#         llm_output = llm_to_use.invoke(task)
#         extracted_name = (llm_output.content or "").strip()

#         # If LLM returned nothing useful, early return
#         if not extracted_name:
#             return {"status": "not_found", "reason": "LLM did not extract a list name", "query": query}

#         # 2) Fetch all lists for the board and build name -> id map
#         try:
#             lists_resp = toolset.execute_action(params={"idBoard": idBoard}, action="TRELLO_GET_BOARDS_LISTS_BY_ID_BOARD")
#         except Exception as e:
#             return {"status": "error", "reason": f"Failed to fetch board lists: {e}"}

#         lists_details = lists_resp.get("data", {}).get("details", []) or []
#         # Build mapping and also keep a list of names for debug/feedback
#         name_to_id_map: Dict[str, str] = {}
#         for lst in lists_details:
#             name = lst.get("name", "")
#             lid = lst.get("id")
#             if name and lid:
#                 name_to_id_map[name] = lid

#         # 3) Find the list id for the extracted list name
#         # Try exact match (case-sensitive), then case-insensitive
#         list_id = None
#         if extracted_name in name_to_id_map:
#             list_id = name_to_id_map[extracted_name]
#             matched_name = extracted_name
#         else:
#             # case-insensitive match
#             lower_to_original = {k.lower(): k for k in name_to_id_map.keys()}
#             key_lower = extracted_name.lower()
#             if key_lower in lower_to_original:
#                 matched_name = lower_to_original[key_lower]
#                 list_id = name_to_id_map[matched_name]
#             else:
#                 # try substring contains (list name contains extracted_name or vice-versa)
#                 matched_name = None
#                 for existing in name_to_id_map:
#                     if extracted_name.lower() in existing.lower() or existing.lower() in extracted_name.lower():
#                         matched_name = existing
#                         list_id = name_to_id_map[existing]
#                         break

#         if not list_id:
#             return {
#                 "status": "not_found",
#                 "extracted_name": extracted_name,
#                 "available_lists": list(list(name_to_id_map.keys())),
#                 "message": "No matching list found"
#             }

#         # 4) Fetch cards for the matched list
#         card_details = []
#         try:
#             cards_resp = toolset.execute_action(params={"idList": list_id}, action="TRELLO_GET_LISTS_CARDS_BY_ID_LIST")
#             card_details = cards_resp.get("data", {}).get("details", []) or []
#         except Exception as e:
#             return {"status": "error", "reason": f"Failed to fetch cards for list {list_id}: {e}", "list_id": list_id, "list_name": matched_name}
        
#         # If no cards found, return early
#         if not card_details:
#             return {
#                 "status": "success",
#                 "list_name": matched_name or extracted_name,
#                 "list_id": list_id,
#                 "tasks": [],
#                 "total_tasks": 0
#             }

#         # 5) For each card, extract tasks (checklist items) - NOT checklists themselves
#         all_tasks = []
#         for card in card_details:
#             card_id = card.get("id")
#             card_name = card.get("name", "Unnamed Card")
            
#             if not card_id:
#                 continue
            
#             # First, check if card already contains checkItems directly (some API responses include them)
#             card_checkItems = []
#             if "checkItems" in card and isinstance(card["checkItems"], list):
#                 card_checkItems = card["checkItems"]
#             elif "checkitems" in card and isinstance(card["checkitems"], list):
#                 card_checkItems = card["checkitems"]
            
#             # If card has checkItems directly, use them and skip fetching checklists
#             if card_checkItems:
#                 for item in card_checkItems:
#                     if isinstance(item, dict):
#                         item_name = item.get("name", "")
#                         if item_name:
#                             all_tasks.append(item_name)
#                 continue  # Skip fetching checklists if we already got items from card
            
#             # Otherwise, fetch checklists for this card
#             checklists = []
#             try:
#                 checklists_resp = toolset.execute_action(
#                     params={"idCard": card_id}, 
#                     action="TRELLO_GET_CARDS_CHECKLISTS_BY_ID_CARD"
#                 )
                
#                 # Parse checklists from response - handle multiple formats
#                 if isinstance(checklists_resp, list):
#                     checklists = checklists_resp
#                 elif isinstance(checklists_resp, dict):
#                     # Check for data.details
#                     data = checklists_resp.get("data", {})
#                     if isinstance(data, dict):
#                         details = data.get("details", [])
#                         if isinstance(details, list):
#                             checklists = details
#                         elif isinstance(details, dict) and details.get("id"):
#                             checklists = [details]
#                         # Also check for checklists key
#                         elif "checklists" in data and isinstance(data["checklists"], list):
#                             checklists = data["checklists"]
#                     elif isinstance(data, list):
#                         checklists = data
#                     # Check if response has checklists at top level
#                     elif "checklists" in checklists_resp and isinstance(checklists_resp["checklists"], list):
#                         checklists = checklists_resp["checklists"]
#                     # If it's a single checklist dict with id
#                     elif "id" in checklists_resp:
#                         checklists = [checklists_resp]
#             except Exception as e:
#                 # Card might not have checklists, continue to next card
#                 # Don't silently fail - log the error for debugging
#                 import traceback
#                 print(f"DEBUG: Failed to fetch checklists for card {card_name} ({card_id}): {e}")
#                 print(f"DEBUG: Traceback: {traceback.format_exc()}")
#                 # Also try to print the raw response if available
#                 try:
#                     print(f"DEBUG: checklists_resp type: {type(checklists_resp)}, value: {checklists_resp}")
#                 except:
#                     pass
#                 continue
            
#             # Debug: print how many checklists we found
#             print(f"DEBUG: Found {len(checklists)} checklists for card {card_name} ({card_id})")
            
#             # For each checklist, get its items
#             for checklist in checklists:
#                 if not isinstance(checklist, dict):
#                     print(f"DEBUG: Checklist is not a dict: {type(checklist)}")
#                     continue
                
#                 checklist_name = checklist.get("name", "Unnamed Checklist")
#                 print(f"DEBUG: Processing checklist: {checklist_name}")
                
#                 # First, check if checklist already contains checkItems (some API responses include them)
#                 items = []
#                 if "checkItems" in checklist and isinstance(checklist["checkItems"], list):
#                     items = checklist["checkItems"]
#                     print(f"DEBUG: Found {len(items)} items embedded in checklist")
#                 elif "items" in checklist and isinstance(checklist["items"], list):
#                     items = checklist["items"]
#                     print(f"DEBUG: Found {len(items)} items in 'items' field")
                
#                 # If items not found in checklist, fetch them separately
#                 if not items:
#                     # Extract checklist ID - try multiple fields
#                     checklist_id = checklist.get("id") or checklist.get("checklist_id") or checklist.get("idChecklist")
                    
#                     if not checklist_id:
#                         print(f"DEBUG: No checklist_id found in checklist. Keys: {list(checklist.keys())[:10]}")
#                         continue
                    
#                     print(f"DEBUG: Fetching items for checklist {checklist_id}")
                    
#                     # Fetch checklist items
#                     try:
#                         items_resp = toolset.execute_action(
#                             params={"idCard": card_id, "idChecklist": checklist_id},
#                             action="TRELLO_GET_CARDS_CHECKLIST_CHECK_ITEMS_BY_ID_CARD_BY_ID_CHECKLIST"
#                         )
                        
#                         print(f"DEBUG: Items response type: {type(items_resp)}")
#                         if isinstance(items_resp, dict):
#                             print(f"DEBUG: Items response keys: {list(items_resp.keys())[:10]}")
                        
#                         # Parse items from response - handle multiple formats
#                         if isinstance(items_resp, list):
#                             items = items_resp
#                             print(f"DEBUG: Items is a list with {len(items)} items")
#                         elif isinstance(items_resp, dict):
#                             # Check for data.details
#                             data = items_resp.get("data", {})
#                             if isinstance(data, dict):
#                                 details = data.get("details", [])
#                                 if isinstance(details, list):
#                                     items = details
#                                     print(f"DEBUG: Found items in data.details: {len(items)} items")
#                                 elif isinstance(details, dict) and details.get("id"):
#                                     items = [details]
#                                     print(f"DEBUG: Found single item in data.details")
#                                 # Also check for checkItems key
#                                 elif "checkItems" in data and isinstance(data["checkItems"], list):
#                                     items = data["checkItems"]
#                                     print(f"DEBUG: Found items in data.checkItems: {len(items)} items")
#                             elif isinstance(data, list):
#                                 items = data
#                                 print(f"DEBUG: Found items in data (list): {len(items)} items")
#                             # Check if response has checkItems at top level
#                             elif "checkItems" in items_resp and isinstance(items_resp["checkItems"], list):
#                                 items = items_resp["checkItems"]
#                                 print(f"DEBUG: Found items in top-level checkItems: {len(items)} items")
#                             # If it's a single item dict with id
#                             elif "id" in items_resp:
#                                 items = [items_resp]
#                                 print(f"DEBUG: Single item dict found")
#                             else:
#                                 # Try to find any list-like structure
#                                 for key in items_resp.keys():
#                                     val = items_resp[key]
#                                     if isinstance(val, list) and len(val) > 0:
#                                         if isinstance(val[0], dict) and ("name" in val[0] or "text" in val[0]):
#                                             items = val
#                                             print(f"DEBUG: Found items in key '{key}': {len(items)} items")
#                                             break
                        
#                         # Debug: print what we got
#                         if not items:
#                             print(f"DEBUG: No items found in response for checklist {checklist_id}")
#                             if isinstance(items_resp, dict):
#                                 print(f"DEBUG: Full response structure: {list(items_resp.keys())}")
#                                 # Try to print a sample of the response
#                                 import json
#                                 try:
#                                     print(f"DEBUG: Response sample: {json.dumps(items_resp, indent=2, default=str)[:500]}")
#                                 except:
#                                     print(f"DEBUG: Could not serialize response")
#                     except Exception as e:
#                         # Failed to fetch items for this checklist, continue to next
#                         import traceback
#                         print(f"DEBUG: Failed to fetch items for checklist {checklist_id} on card {card_name}: {e}")
#                         print(f"DEBUG: Traceback: {traceback.format_exc()}")
#                         continue
                
#                 # Extract task names from items - just store task names, not checklist info
#                 print(f"DEBUG: Extracting task names from {len(items)} items")
#                 for item in items:
#                     if isinstance(item, dict):
#                         item_name = item.get("name", "") or item.get("text", "")
#                         if item_name:
#                             all_tasks.append(item_name)
#                             print(f"DEBUG: Added task: {item_name[:50]}...")
#                         else:
#                             print(f"DEBUG: Item has no 'name' or 'text' field. Item keys: {list(item.keys())[:5]}")
#                     else:
#                         print(f"DEBUG: Item is not a dict: {type(item)}, value: {str(item)[:50]}")
        
#         # 6) Return structured data with just task names
#         return {
#             "status": "success",
#             "list_name": matched_name or extracted_name,
#             "list_id": list_id,
#             "tasks": all_tasks,
#             "total_tasks": len(all_tasks)
#         }
    
#     async def get_deadline(self, idBoard: str, query: str):
#         """
#         Extract card name from query, find matching cards, convert deadlines to IST,
#         compute time-left and sort ascending by time-left.
#         Returns a structured dict with matches + llm_summary.
#         """
#         llm_to_use = self.llm or llm
#         if not llm_to_use:
#             raise RuntimeError("LLM not initialized. Please provide gemini_api_key.")

#         # 1) extract card name
#         task = f"""You are a card name extractor expert. Extract only the card name.
# User query: {query}
# """
#         res = llm_to_use.invoke(task)
#         card_name = (res.content or "").strip()
#         if not card_name:
#             return {"status": "not_found", "reason": "LLM did not extract a card name", "query": query}

#         # 2) fetch all cards from board
#         try:
#             response = self.toolset.execute_action(params={"idBoard": idBoard}, action="TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD")
#         except Exception as e:
#             return {"status": "error", "reason": f"failed to fetch cards for board {idBoard}: {e}"}

#         cards = response.get("data", {}).get("details", []) or []

#         # 3) prepare IST timezone & now
#         if HAVE_ZONEINFO:
#             ist_tz = ZoneInfo("Asia/Kolkata")
#             now_ist = datetime.now(ist_tz)
#         else:
#             ist_tz = pytz.timezone("Asia/Kolkata")
#             now_ist = datetime.now(ist_tz)

#         def parse_iso_to_aware(dt_str: Optional[str]) -> Optional[datetime]:
#             if not dt_str:
#                 return None
#             s = dt_str
#             if s.endswith("Z"):
#                 s = s[:-1] + "+00:00"
#             try:
#                 dt_utc = datetime.fromisoformat(s)
#             except Exception:
#                 # try fallback
#                 try:
#                     dt_naive = datetime.strptime(dt_str, "%Y-%m-%dT%H:%M:%S")
#                     if HAVE_ZONEINFO:
#                         dt_utc = dt_naive.replace(tzinfo=ZoneInfo("UTC"))
#                     else:
#                         dt_utc = pytz.UTC.localize(dt_naive)
#                 except Exception:
#                     return None
#             # convert to IST
#             return dt_utc.astimezone(ist_tz)

#         matches = []
#         for c in cards:
#             name = c.get("name", "") or ""
#             if name.lower() == card_name.lower() or card_name.lower() in name.lower():
#                 due_raw = c.get("due")
#                 due_dt_ist = parse_iso_to_aware(due_raw)
#                 time_left = (due_dt_ist - now_ist) if due_dt_ist else None
#                 matches.append({
#                     "id": c.get("id"),
#                     "card_name": name,
#                     "deadline_ist": due_dt_ist.isoformat() if due_dt_ist else None,
#                     "time_left_timedelta": time_left
#                 })

#         if not matches:
#             return {"status": "not_found", "reason": f"No card matching '{card_name}' found on board {idBoard}."}

#         def sort_key(x):
#             return x["time_left_timedelta"] if x["time_left_timedelta"] is not None else timedelta.max

#         matches_sorted = sorted(matches, key=sort_key)

#         def fmt_timedelta(td: Optional[timedelta]) -> str:
#             if td is None:
#                 return "No deadline assigned"
#             total_seconds = int(td.total_seconds())
#             sign = ""
#             if total_seconds < 0:
#                 sign = "-"
#                 total_seconds = abs(total_seconds)
#             days, rem = divmod(total_seconds, 86400)
#             hours, rem = divmod(rem, 3600)
#             minutes, seconds = divmod(rem, 60)
#             parts = []
#             if days:
#                 parts.append(f"{days}d")
#             if hours:
#                 parts.append(f"{hours}h")
#             if minutes:
#                 parts.append(f"{minutes}m")
#             if not parts:
#                 parts.append(f"{seconds}s")
#             return sign + " ".join(parts)

#         # build text for LLM
#         deadlines_text_lines = []
#         for m in matches_sorted:
#             deadline_str = m["deadline_ist"] or "No deadline assigned"
#             time_left_str = fmt_timedelta(m["time_left_timedelta"])
#             deadlines_text_lines.append(f"Card: {m['card_name']}, Deadline(IST): {deadline_str}, Time Left: {time_left_str}")

#         deadlines_text = "\n".join(deadlines_text_lines)

#         llm_prompt = f"""
#             You are a deadline summarizer.
#             Current IST time: {now_ist.strftime('%Y-%m-%d %H:%M:%S %Z')}

#             Below are deadlines (sorted by increasing time left):

#             {deadlines_text}

#             Please return the summary formatted as:

#             Few Deadlines are approaching for the cards (Please modify this statement according to the query asked):
#             1) Card: <card_name>, Deadline: <deadline>, Time Left: <time_left>
#             2) ...

#             If a card has no deadline, mention 'No deadline assigned'.
#             """
#         llm_to_use = self.llm or llm
#         summary_output = llm_to_use.invoke(llm_prompt) if llm_to_use else None
#         summary_text = getattr(summary_output, "content", None) if summary_output else None

#         return summary_text

#     async def get_all_deadlines(self, idBoard: str, query: str) -> Dict[str, Any]:
#         """
#         Fetch all deadlines on the board, sort them by urgency (closest deadline first),
#         and return a structured result plus an LLM-produced human-friendly summary.
#         The `main_task` prompt is kept exactly as you requested and is used as the LLM prompt prefix.
#         """
#         # ensure toolset on self
#         if not hasattr(self, "toolset"):
#             self.toolset = ComposioToolSet(api_key=composio_api_key)

#         # keep your original main_task prompt exactly (with the query interpolated)
#         main_task = f""" You are a all deadline fetching expert, you're the main person who tells a user about his/her upcoming deadlines.
#         Here you're specifically designed for fetching the deadlines of all the cards from Trello of a a particular board. 
#         The user query could be anything like : Fetch all the pending deadlines or What more work is remaining? or Give the sequence of the tasks
#         that needs to be performed etc. The query could be anything related to the above queries, you should be able to extract the task of fetching the 
#         pending deadlines with the task names using a json provoided below. And also you should modify the output or the starting statement of the output according to the query

#         expected output: The first line or the starting statement should be given as like a how a normal human being will start answering the
#         query: {query}
#         Next, thing to output is the pointwise distribution of the deadlines arranges with their whole card context and also they should be
#         arranged in a priority order from most close deadline to the farthest deadline.

#         I want the output in the above mentioned format only, NOTHING MORE.
#         """

#         # 1) fetch all cards from board
#         try:
#             resp = self.toolset.execute_action(params={"idBoard": idBoard}, action="TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD")
#         except Exception as e:
#             return {"status": "error", "reason": f"Failed to fetch board cards: {e}"}

#         cards = resp.get("data", {}).get("details", []) or []

#         # 2) prepare IST timezone & now
#         try:
#             if HAVE_ZONEINFO:
#                 ist_tz = ZoneInfo("Asia/Kolkata")
#             else:
#                 ist_tz = pytz.timezone("Asia/Kolkata")
#             now_ist = datetime.now(ist_tz)
#         except Exception:
#             # fallback
#             ist_tz = pytz.timezone("Asia/Kolkata")
#             now_ist = datetime.now(ist_tz)

#         # helper to parse Trello ISO datetimes into aware IST datetimes
#         def parse_iso_to_ist(dt_str: Optional[str]) -> Optional[datetime]:
#             if not dt_str:
#                 return None
#             s = dt_str
#             if s.endswith("Z"):
#                 s = s[:-1] + "+00:00"
#             try:
#                 dt = datetime.fromisoformat(s)  # may be aware or naive-with-offset
#             except Exception:
#                 # fallback common formats
#                 dt = None
#                 try:
#                     dt_naive = datetime.strptime(dt_str.split(".")[0], "%Y-%m-%dT%H:%M:%S")
#                     # assume UTC
#                     if HAVE_ZONEINFO:
#                         dt = dt_naive.replace(tzinfo=ZoneInfo("UTC"))
#                     else:
#                         dt = pytz.UTC.localize(dt_naive)
#                 except Exception:
#                     dt = None
#                 if not dt:
#                     return None
#             # convert to IST tz
#             try:
#                 return dt.astimezone(ist_tz)
#             except Exception:
#                 try:
#                     if dt.tzinfo is None:
#                         if HAVE_ZONEINFO:
#                             dt = dt.replace(tzinfo=ZoneInfo("UTC"))
#                         else:
#                             dt = pytz.UTC.localize(dt)
#                     return dt.astimezone(ist_tz)
#                 except Exception:
#                     return None

#         # 3) collect only cards that have a deadline (pending or overdue)
#         matches: List[Dict[str, Any]] = []
#         for c in cards:
#             card_id = c.get("id")
#             name = c.get("name")
#             desc = c.get("desc") or ""
#             idList = c.get("idList")
#             url = c.get("url") or c.get("shortUrl")
#             due_raw = c.get("due")
#             due_ist = parse_iso_to_ist(due_raw)
#             if due_ist:
#                 time_left = due_ist - now_ist
#                 matches.append({
#                     "id": card_id,
#                     "name": name,
#                     "description": desc,
#                     "idList": idList,
#                     "url": url,
#                     "deadline_ist": due_ist.isoformat(),
#                     "time_left_timedelta": time_left
#                 })

#         if not matches:
#             return {
#                 "status": "no_deadlines",
#                 "now_ist": now_ist.isoformat(),
#                 "total_cards": len(cards),
#                 "deadlines_count": 0,
#                 "matches": [],
#                 "llm_summary": None,
#                 "message": "No deadlines found on this board."
#             }

#         # 4) sort by increasing time_left (earliest/most urgent first). overdue (negative) will come first.
#         def sort_key(x):
#             return x["time_left_timedelta"] if x["time_left_timedelta"] is not None else timedelta.max

#         matches_sorted = sorted(matches, key=sort_key)

#         # 5) human-friendly time-left formatter
#         def fmt_timedelta(td: Optional[timedelta]) -> str:
#             if td is None:
#                 return "No deadline assigned"
#             total_seconds = int(td.total_seconds())
#             sign = ""
#             if total_seconds < 0:
#                 sign = "-"  # overdue
#                 total_seconds = abs(total_seconds)
#             days, rem = divmod(total_seconds, 86400)
#             hours, rem = divmod(rem, 3600)
#             minutes, seconds = divmod(rem, 60)
#             parts = []
#             if days:
#                 parts.append(f"{days}d")
#             if hours:
#                 parts.append(f"{hours}h")
#             if minutes:
#                 parts.append(f"{minutes}m")
#             if not parts:
#                 parts.append(f"{seconds}s")
#             return sign + " ".join(parts)

#         # 6) build concise block of deadlines to append to main_task for the LLM
#         block_lines = []
#         for i, m in enumerate(matches_sorted, start=1):
#             short_desc = (m["description"][:300] + "…") if m["description"] and len(m["description"]) > 300 else (m["description"] or "No description")
#             block_lines.append(
#                 f"{i}) Card: {m['name']}\n"
#                 f"   - Card ID: {m['id']}\n"
#                 f"   - Deadline (IST): {m['deadline_ist']}\n"
#                 f"   - Time left: {fmt_timedelta(m['time_left_timedelta'])}\n"
#                 f"   - Short description: {short_desc}\n"
#                 f"   - URL: {m.get('url') or 'N/A'}\n"
#             )
#         cards_block = "\n".join(block_lines)

#         # 7) final LLM prompt: keep main_task and append the structured deadlines block and explicit formatting instruction
#         llm_prompt = "\n\n".join([
#             main_task,
#             "Below are the deadlines extracted (already sorted from most urgent to farthest):",
#             cards_block,
#             "",
#             "Please respond EXACTLY in this format:",
#             "First line: a natural one-line opening that answers the user's query.",
#             "Then a point-wise list where each point is 'Card: <name>, Deadline: <deadline>, Time Left: <time_left>' followed by one short line of combined context (short description).",
#             "Keep the order the same as provided (most urgent first). NOTHING MORE."
#         ])

#         # 8) call LLM to generate human-friendly summary (if llm available)
#         try:
#             llm_to_use = self.llm or llm
#             llm_output = llm_to_use.invoke(llm_prompt) if llm_to_use else None
#             llm_summary = getattr(llm_output, "content", None) if llm_output else None
#         except Exception:
#             llm_summary = None

#         # 9) return structured result (single function)
#         return llm_summary

#         # async def get_card_description(idBoard: str):
#             ## 1st get all cards from the board_id using TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD
#             ## first filter out using the name of the card, when found, then filter out what we need and then return 


#         # async def get_card_comment(idBoard: str):
#         #     ## same as the get_card_description, fetch card comments bas

# #     async def get_checklist(self, idBoard: str, query: str) -> Dict[str, Any]:
# #         """
# #         Fetch all incomplete checklist items on the board `idBoard` and produce a detailed LLM response.
# #         Returns:
# #           {
# #             "status": "success" | "no_pending" | "error",
# #             "results": {
# #                 "<card_id>": {
# #                     "card_name": "<name or None>",
# #                     "deadline": "<iso or None>",
# #                     "tasks": [
# #                         {"item_id": "<id>", "text": "<task text>", "state": "Incomplete" }
# #                     ]
# #                 }, ...
# #             },
# #             "llm_summary": "<human-friendly text>"
# #           }
# #         """
# #         # ensure toolset exists
# #         if not hasattr(self, "toolset") or self.toolset is None:
# #             self.toolset = ComposioToolSet(api_key=composio_api_key)

# #         # helper: normalize dict/list shapes into list of dicts (shallow flatten)
# #         def normalize_to_list_of_dicts(obj):
# #             out = []
# #             if obj is None:
# #                 return out
# #             if isinstance(obj, list):
# #                 for it in obj:
# #                     if isinstance(it, dict):
# #                         out.append(it)
# #                     elif isinstance(it, list):
# #                         out.extend(normalize_to_list_of_dicts(it))
# #                 return out
# #             if isinstance(obj, dict):
# #                 # sometimes details may contain a list in a field; try common fields
# #                 if "details" in obj and isinstance(obj["details"], (list, dict)):
# #                     return normalize_to_list_of_dicts(obj["details"])
# #                 if "items" in obj and isinstance(obj["items"], (list, dict)):
# #                     return normalize_to_list_of_dicts(obj["items"])
# #                 # otherwise wrap the dict as single element
# #                 return [obj]
# #             # if it's a raw string, return empty list (we'll parse text separately)
# #             return out

# #         # helper: parse plain-text output like your example into checklist entries
# #         def parse_checklists_text(text: str):
# #             """
# #             Returns list of items: { 'card_id':..., 'item_id':..., 'text':..., 'state':... }
# #             Heuristic parser designed for outputs similar to the sample you provided.
# #             """
# #             items = []
# #             if not text:
# #                 return items

# #             lines = [ln.rstrip() for ln in text.splitlines()]
# #             last_nonempty = None
# #             current_card = None
# #             current_checklist = None

# #             for i, ln in enumerate(lines):
# #                 s = ln.strip()
# #                 if not s:
# #                     continue
# #                 # detect Associated Card ID
# #                 m_card = re.match(r'Associated\s+Card\s+ID\s*[:\-]\s*(\S+)', s, flags=re.IGNORECASE)
# #                 if m_card:
# #                     current_card = m_card.group(1).strip()
# #                     # reset checklist context
# #                     current_checklist = None
# #                     last_nonempty = s
# #                     continue

# #                 # detect checklist header
# #                 m_chk = re.match(r'Checklist\s*[:\-]\s*(.+)', s, flags=re.IGNORECASE)
# #                 if m_chk:
# #                     current_checklist = m_chk.group(1).strip()
# #                     last_nonempty = s
# #                     continue

# #                 # detect item ID lines - we ignore them for item text but keep last_nonempty as candidate text
# #                 if re.match(r'ID\s*[:\-]\s*([A-Za-z0-9]+)', s, flags=re.IGNORECASE):
# #                     # keep last_nonempty as the task text if it's not one of the metadata lines
# #                     last_nonempty = last_nonempty
# #                     continue

# #                 # detect state lines
# #                 m_state = re.match(r'State\s*[:\-]\s*(\w+)', s, flags=re.IGNORECASE)
# #                 if m_state:
# #                     state = m_state.group(1).strip()
# #                     # item text is best guess: the last_nonempty line that is not metadata
# #                     item_text = None
# #                     if last_nonempty and not re.match(r'^(ID|State|Position|Checklist|Associated)', last_nonempty, flags=re.IGNORECASE):
# #                         item_text = last_nonempty.strip()
# #                     # try fallback: look one or two lines above for a possible text
# #                     if not item_text:
# #                         # search backwards for a line that is not metadata
# #                         for j in range(i-1, max(-1, i-5), -1):
# #                             cand = lines[j].strip()
# #                             if cand and not re.match(r'^(ID|State|Position|Checklist|Associated|Task\s*\d+)', cand, flags=re.IGNORECASE):
# #                                 item_text = cand
# #                                 break
# #                     items.append({
# #                         "card_id": current_card,
# #                         "checklist": current_checklist,
# #                         "item_id": None,   # we don't reliably capture item-id from this heuristic
# #                         "text": item_text or "<unknown task text>",
# #                         "state": state
# #                     })
# #                     last_nonempty = s
# #                     continue

# #                 # update last_nonempty for potential task names
# #                 last_nonempty = s

# #             return items

# #         # 1) call Composio checklist tool
# #         try:
# #             raw_chk_resp = self.toolset.execute_action(params={"idBoard": idBoard}, action="TRELLO_GET_BOARDS_CHECKLISTS_BY_ID_BOARD")
# #         except Exception as e:
# #             return {"status": "error", "reason": f"Failed to execute checklist tool: {e}"}

# #         # 2) try to extract structured checklist items
# #         checklist_items = []  # will collect items of shape {card_id, item_id, text, state}
# #         try:
# #             if isinstance(raw_chk_resp, dict):
# #                 # try common structured locations
# #                 data = raw_chk_resp.get("data") or raw_chk_resp
# #                 # sometimes details is list of checklists
# #                 possible_lists = []
# #                 if isinstance(data, dict) and "details" in data:
# #                     possible_lists = data.get("details") or []
# #                 elif isinstance(data, dict) and "items" in data:
# #                     possible_lists = data.get("items") or []
# #                 elif isinstance(data, list):
# #                     possible_lists = data
# #                 elif isinstance(data, dict) and all(isinstance(v, dict) for v in data.values()):
# #                     # dict-of-dicts -> convert to list
# #                     possible_lists = list(data.values())
# #                 else:
# #                     # fallback: try to find any nested checklist-like dicts
# #                     possible_lists = []
# #                     for k, v in (data.items() if isinstance(data, dict) else []):
# #                         if isinstance(v, list):
# #                             possible_lists.extend(v)

# #                 # Normalize per-checklist structure
# #                 for chk in normalize_to_list_of_dicts(possible_lists):
# #                     # identify associated card id
# #                     assoc_card = chk.get("idCard") or chk.get("cardId") or chk.get("associatedCardId") or chk.get("card_id") or chk.get("associated_card_id")
# #                     # items can be in 'checkItems', 'items', or nested
# #                     raw_items = chk.get("checkItems") or chk.get("items") or chk.get("check_items") or []
# #                     for it in normalize_to_list_of_dicts(raw_items):
# #                         state = it.get("state") or it.get("checkedState") or it.get("status") or ""
# #                         text = it.get("name") or it.get("text") or it.get("title") or None
# #                         item_id = it.get("id") or it.get("checkItemId")
# #                         checklist_items.append({
# #                             "card_id": assoc_card,
# #                             "checklist": chk.get("name") or chk.get("checklist") or None,
# #                             "item_id": item_id,
# #                             "text": text or "<no text>",
# #                             "state": state or ""
# #                         })
# #                 # If nothing extracted from structured form, maybe the tool returned a plain-text 'message' or string
# #                 if not checklist_items:
# #                     # attempt to find textual field in response
# #                     textual = None
# #                     for key in ("message", "text", "output", "result"):
# #                         if isinstance(data, dict) and key in data and isinstance(data[key], str):
# #                             textual = data[key]
# #                             break
# #                     if isinstance(raw_chk_resp, str):
# #                         textual = raw_chk_resp
# #                     if textual:
# #                         checklist_items = parse_checklists_text(textual)
# #             elif isinstance(raw_chk_resp, list):
# #                 # assume list of checklists
# #                 for chk in raw_chk_resp:
# #                     if not isinstance(chk, dict):
# #                         continue
# #                     assoc_card = chk.get("idCard") or chk.get("cardId")
# #                     raw_items = chk.get("checkItems") or chk.get("items") or []
# #                     for it in normalize_to_list_of_dicts(raw_items):
# #                         checklist_items.append({
# #                             "card_id": assoc_card,
# #                             "checklist": chk.get("name"),
# #                             "item_id": it.get("id"),
# #                             "text": it.get("name") or it.get("text") or "<no text>",
# #                             "state": it.get("state") or ""
# #                         })
# #             elif isinstance(raw_chk_resp, str):
# #                 # plain-text fallback (the sample you pasted)
# #                 checklist_items = parse_checklists_text(raw_chk_resp)
# #         except Exception as e:
# #             # parsing error - attempt best-effort textual parse
# #             try:
# #                 textual = str(raw_chk_resp)
# #                 checklist_items = parse_checklists_text(textual)
# #             except Exception:
# #                 return {"status": "error", "reason": f"Failed parsing checklist output: {e}"}

# #         # 3) filter only incomplete items (case-insensitive match on 'incomplete')
# #         incomplete_items = [it for it in checklist_items if it.get("state") and it.get("state").strip().lower().startswith("incomplete")]
# #         if not incomplete_items:
# #             return {"status": "no_pending", "results": {}, "llm_summary": None}

# #         # 4) fetch board cards to map card id -> name and deadline
# #         card_map = {}
# #         try:
# #             cards_resp = self.toolset.execute_action(params={"idBoard": idBoard}, action="TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD")
# #             card_raw = cards_resp.get("data") if isinstance(cards_resp, dict) and "data" in cards_resp else cards_resp
# #             # try to extract list
# #             possible_cards = None
# #             if isinstance(card_raw, dict) and "details" in card_raw:
# #                 possible_cards = card_raw["details"]
# #             elif isinstance(card_raw, dict) and "items" in card_raw:
# #                 possible_cards = card_raw["items"]
# #             elif isinstance(card_raw, list):
# #                 possible_cards = card_raw
# #             elif isinstance(card_raw, dict):
# #                 possible_cards = list(card_raw.values())
# #             else:
# #                 possible_cards = []
# #             for c in normalize_to_list_of_dicts(possible_cards):
# #                 cid = c.get("id") or c.get("idCard")
# #                 if not cid:
# #                     continue
# #                 card_map[cid] = {
# #                     "name": c.get("name") or c.get("title") or None,
# #                     "deadline": c.get("due") or c.get("deadline") or None,
# #                     "_raw": c
# #                 }
# #         except Exception:
# #             # if cards fetch fails, we will just keep card names as None
# #             card_map = {}

# #         # 5) group incomplete items by card_id and build structured results
# #         results = {}
# #         for it in incomplete_items:
# #             cid = it.get("card_id")
# #             if not cid:
# #                 cid = "<unknown_card>"
# #             entry = results.setdefault(cid, {"card_name": None, "deadline": None, "tasks": []})
# #             # fill card info if available
# #             if cid in card_map:
# #                 entry["card_name"] = card_map[cid].get("name")
# #                 entry["deadline"] = card_map[cid].get("deadline")
# #             # append task
# #             entry["tasks"].append({
# #                 "item_id": it.get("item_id"),
# #                 "text": it.get("text"),
# #                 "state": it.get("state")
# #             })

# #         # 6) build LLM prompt to produce human-friendly output in requested format
# #         # Build a compact block of the findings for LLM
# #         block_lines = []
# #         for cid, info in results.items():
# #             title = info.get("card_name") or f"(card id: {cid})"
# #             dl = info.get("deadline") or "No deadline"
# #             block_lines.append(f"Card: {title}\nCardID: {cid}\nDeadline: {dl}\nTasks:")
# #             for t in info["tasks"]:
# #                 block_lines.append(f"  - {t['text']}  (Status: {t['state']})")

# #         items_block = "\n".join(block_lines)

# #         llm_prompt = f"""
# #         You are an expert assistant that reports the pending tasks of a user which are defined in a card's checklist. You report all the pendings tasks in a very organised manner
# #         and you are master at your job. The input you task is firstly the query. Make sure you start the output in such a way that it seems like you're a normal human replying to their 
# #         query.I WANT THE OUTPUT FORMAT TO DEPEND UPON USER INPUT FORMAT. 

# #         -------------------INPUT-----------------
# #         User query: {query}
# #         Below are the incomplete checklist items found on board {idBoard} (grouped by card):
# #         {items_block}
# #         ---------------------------------------------------------------

# #         The format that your master GENERALLU accept is :
# #         ---------------------------------------------------------------
# #         The first output line :
# #         Board Id and Card Name: (expand a bit here)
# #         List all the tasks pending point wise like
# #         1) task-1 if deadline, mention that
# #         2) task-2 if deadline, mention that

# #         Also I want u to convert the deadline format into this format
# #         "Date (like eg: 25th), Month (like eg: October). Time (eg: 12pm)
# #         ------------------------------------------------------
# #          But if the user wants the percentage of tasks pendings then you should return the percentage of the incomplete tasks.
# #         NOTHING MORE IS NEEDED. I DONT NEED YOUR ACKNOWLEDGEMENT, I NEED THE OUTPUT ONLY. DON'T RETURN  --------INPUT------- FORMAT OR ---------OUTPUT FORMAT-----------

# # """
# #         # 7) call LLM to generate final summary (if available)
# #         try:
# #             llm_out = llm.invoke(llm_prompt) if llm else None
# #             llm_summary = getattr(llm_out, "content", None) if llm_out else None
# #         except Exception:
# #             llm_summary = None

# #         return  llm_summary
      
#     async def get_checklist(self, idBoard: str, query: str) -> Dict[str, Any]:
#         """
#         Fetch all checklist items (both complete and incomplete) on the board `idBoard` and produce a detailed LLM response.
#         Returns a human-friendly LLM summary string (same behaviour as original function returned), and keeps a structured results map while doing so.
#         """
#         # ensure toolset exists
#         if not hasattr(self, "toolset") or self.toolset is None:
#             self.toolset = ComposioToolSet(api_key=composio_api_key)

#         def normalize_to_list_of_dicts(obj):
#             out = []
#             if obj is None:
#                 return out
#             if isinstance(obj, list):
#                 for it in obj:
#                     if isinstance(it, dict):
#                         out.append(it)
#                     elif isinstance(it, list):
#                         out.extend(normalize_to_list_of_dicts(it))
#                 return out
#             if isinstance(obj, dict):
#                 if "details" in obj and isinstance(obj["details"], (list, dict)):
#                     return normalize_to_list_of_dicts(obj["details"])
#                 if "items" in obj and isinstance(obj["items"], (list, dict)):
#                     return normalize_to_list_of_dicts(obj["items"])
#                 return [obj]
#             return out

#         def parse_checklists_text(text: str):
#             items = []
#             if not text:
#                 return items
#             lines = [ln.rstrip() for ln in text.splitlines()]
#             last_nonempty = None
#             current_card = None
#             current_checklist = None
#             for i, ln in enumerate(lines):
#                 s = ln.strip()
#                 if not s:
#                     continue
#                 m_card = re.match(r'Associated\s+Card\s+ID\s*[:\-]\s*(\S+)', s, flags=re.IGNORECASE)
#                 if m_card:
#                     current_card = m_card.group(1).strip()
#                     current_checklist = None
#                     last_nonempty = s
#                     continue
#                 m_chk = re.match(r'Checklist\s*[:\-]\s*(.+)', s, flags=re.IGNORECASE)
#                 if m_chk:
#                     current_checklist = m_chk.group(1).strip()
#                     last_nonempty = s
#                     continue
#                 if re.match(r'ID\s*[:\-]\s*([A-Za-z0-9]+)', s, flags=re.IGNORECASE):
#                     last_nonempty = last_nonempty
#                     continue
#                 m_state = re.match(r'State\s*[:\-]\s*(\w+)', s, flags=re.IGNORECASE)
#                 if m_state:
#                     state = m_state.group(1).strip()
#                     item_text = None
#                     if last_nonempty and not re.match(r'^(ID|State|Position|Checklist|Associated)', last_nonempty, flags=re.IGNORECASE):
#                         item_text = last_nonempty.strip()
#                     if not item_text:
#                         for j in range(i-1, max(-1, i-5), -1):
#                             cand = lines[j].strip()
#                             if cand and not re.match(r'^(ID|State|Position|Checklist|Associated|Task\s*\d+)', cand, flags=re.IGNORECASE):
#                                 item_text = cand
#                                 break
#                     items.append({
#                         "card_id": current_card,
#                         "checklist": current_checklist,
#                         "item_id": None,
#                         "text": item_text or "<unknown task text>",
#                         "state": state
#                     })
#                     last_nonempty = s
#                     continue
#                 last_nonempty = s
#             return items

#         # 1) fetch checklists from Composio tool
#         try:
#             raw_chk_resp = self.toolset.execute_action(params={"idBoard": idBoard}, action="TRELLO_GET_BOARDS_CHECKLISTS_BY_ID_BOARD")
#         except Exception as e:
#             return {"status": "error", "reason": f"Failed to execute checklist tool: {e}", "results": {}, "llm_summary": None}

#         # 2) extract structured checklist items (both complete and incomplete)
#         checklist_items = []
#         try:
#             if isinstance(raw_chk_resp, dict):
#                 data = raw_chk_resp.get("data") or raw_chk_resp
#                 possible_lists = []
#                 if isinstance(data, dict) and "details" in data:
#                     possible_lists = data.get("details") or []
#                 elif isinstance(data, dict) and "items" in data:
#                     possible_lists = data.get("items") or []
#                 elif isinstance(data, list):
#                     possible_lists = data
#                 elif isinstance(data, dict) and all(isinstance(v, dict) for v in data.values()):
#                     possible_lists = list(data.values())
#                 else:
#                     possible_lists = []
#                     for k, v in (data.items() if isinstance(data, dict) else []):
#                         if isinstance(v, list):
#                             possible_lists.extend(v)
#                 for chk in normalize_to_list_of_dicts(possible_lists):
#                     assoc_card = chk.get("idCard") or chk.get("cardId") or chk.get("associatedCardId") or chk.get("card_id") or chk.get("associated_card_id")
#                     raw_items = chk.get("checkItems") or chk.get("items") or chk.get("check_items") or []
#                     for it in normalize_to_list_of_dicts(raw_items):
#                         state = it.get("state") or it.get("checkedState") or it.get("status") or ""
#                         text = it.get("name") or it.get("text") or it.get("title") or None
#                         item_id = it.get("id") or it.get("checkItemId")
#                         checklist_items.append({
#                             "card_id": assoc_card,
#                             "checklist": chk.get("name") or chk.get("checklist") or None,
#                             "item_id": item_id,
#                             "text": text or "<no text>",
#                             "state": state or ""
#                         })
#                 if not checklist_items:
#                     textual = None
#                     for key in ("message", "text", "output", "result"):
#                         if isinstance(data, dict) and key in data and isinstance(data[key], str):
#                             textual = data[key]
#                             break
#                     if isinstance(raw_chk_resp, str):
#                         textual = raw_chk_resp
#                     if textual:
#                         checklist_items = parse_checklists_text(textual)
#             elif isinstance(raw_chk_resp, list):
#                 for chk in raw_chk_resp:
#                     if not isinstance(chk, dict):
#                         continue
#                     assoc_card = chk.get("idCard") or chk.get("cardId")
#                     raw_items = chk.get("checkItems") or chk.get("items") or []
#                     for it in normalize_to_list_of_dicts(raw_items):
#                         checklist_items.append({
#                             "card_id": assoc_card,
#                             "checklist": chk.get("name"),
#                             "item_id": it.get("id"),
#                             "text": it.get("name") or it.get("text") or "<no text>",
#                             "state": it.get("state") or ""
#                         })
#             elif isinstance(raw_chk_resp, str):
#                 checklist_items = parse_checklists_text(raw_chk_resp)
#         except Exception as e:
#             try:
#                 textual = str(raw_chk_resp)
#                 checklist_items = parse_checklists_text(textual)
#             except Exception:
#                 return {"status": "error", "reason": f"Failed parsing checklist output: {e}", "results": {}, "llm_summary": None}

#         # 3) if no items found, return no_pending (no items)
#         if not checklist_items:
#             return {"status": "no_items", "results": {}, "llm_summary": None}

#         # 4) fetch board cards to map card id -> name and deadline
#         card_map = {}
#         try:
#             cards_resp = self.toolset.execute_action(params={"idBoard": idBoard}, action="TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD")
#             card_raw = cards_resp.get("data") if isinstance(cards_resp, dict) and "data" in cards_resp else cards_resp
#             possible_cards = None
#             if isinstance(card_raw, dict) and "details" in card_raw:
#                 possible_cards = card_raw["details"]
#             elif isinstance(card_raw, dict) and "items" in card_raw:
#                 possible_cards = card_raw["items"]
#             elif isinstance(card_raw, list):
#                 possible_cards = card_raw
#             elif isinstance(card_raw, dict):
#                 possible_cards = list(card_raw.values())
#             else:
#                 possible_cards = []
#             for c in normalize_to_list_of_dicts(possible_cards):
#                 cid = c.get("id") or c.get("idCard")
#                 if not cid:
#                     continue
#                 card_map[cid] = {
#                     "name": c.get("name") or c.get("title") or None,
#                     "deadline": c.get("due") or c.get("deadline") or None,
#                     "_raw": c
#                 }
#         except Exception:
#             card_map = {}

#         # 5) group all checklist items by card_id
#         results = {}
#         for it in checklist_items:
#             cid = it.get("card_id") or "<unknown_card>"
#             entry = results.setdefault(cid, {"card_name": None, "deadline": None, "tasks": []})
#             if cid in card_map:
#                 entry["card_name"] = card_map[cid].get("name")
#                 entry["deadline"] = card_map[cid].get("deadline")
#             entry["tasks"].append({
#                 "item_id": it.get("item_id"),
#                 "text": it.get("text"),
#                 "state": it.get("state")
#             })

#         # 6) build a compact block of the findings for LLM
#         block_lines = []
#         for cid, info in results.items():
#             title = info.get("card_name") or f"(card id: {cid})"
#             dl = info.get("deadline") or "No deadline"
#             block_lines.append(f"Card: {title}\nCardID: {cid}\nDeadline: {dl}\nTasks:")
#             for t in info["tasks"]:
#                 block_lines.append(f"  - {t['text']}  (Status: {t['state']})")

#         items_block = "\n".join(block_lines)

#         llm_prompt = f"""
#         You are an expert assistant that reports the checklist items (both complete and incomplete) of a user which are defined in cards' checklists. You report all the checklist items in a very organised manner and you are master at your job. The input you task is firstly the query. Make sure you start the output in such a way that it seems like you're a normal human replying to their query.

#         -------------------INPUT-----------------
#         User query: {query}
#         Below are the checklist items found on board {idBoard} (grouped by card):
#         {items_block}
#         ---------------------------------------------------------------

#         The format that your master GENERALLY accept is :
#         ---------------------------------------------------------------
#         The first output line :
#         Board Id and Card Name: (expand a bit here)
#         List all the tasks point wise like
#         1) task-1 if deadline, mention that
#         2) task-2 if deadline, mention that

#         Also I want u to convert the deadline format into this format
#         "Date (like eg: 25th), Month (like eg: October). Time (eg: 12pm)"
#         ------------------------------------------------------
#         NOTHING MORE IS NEEDED. I DONT NEED YOUR ACKNOWLEDGEMENT, I NEED THE OUTPUT ONLY. DON'T RETURN  --------INPUT------- FORMAT OR ---------OUTPUT FORMAT-----------
#         """

#         try:
#             llm_out = llm.invoke(llm_prompt) if llm else None
#             llm_summary = getattr(llm_out, "content", None) if llm_out else None
#         except Exception:
#             llm_summary = None

#         return llm_summary

#     async def get_all_actions(self, idBoard: Optional[str] = None, user_query: Optional[str] = None, query: Optional[str] = None, **kwargs) -> str:
#         """
#         Single self-contained function (no other top-level helpers) that:
#         - robustly fetches lists, cards, members, and actions from Composio/Trello-like endpoints
#         - normalizes common API shapes (handles dict, list/tuple, nested containers)
#         - returns a pointwise human-friendly summary string:
#             1) Board: <name> (ID: `...`)
#             2) Lists & Cards
#                 - <n>. <List name> (List ID: `...`)
#                 - <n>.<m> Card: <name> (ID: `...`)
#                     - Description: ...
#                     - Deadline: ...
#                     - Members: ...
#         Notes:
#         - This single function contains all logic inline (no other top-level functions).
#         - It accepts idBoard OR will attempt to parse a board id from user_query/query.
#         - Assumes `self.toolset` and `composio_api_key` are available in your environment (same as your project).
#         """
#         # local imports so function is self-contained when copied
#         import re
#         from typing import Any, Dict, List, Optional

#         # tolerate different call patterns: prefer explicit idBoard, else try to parse from text
#         actual_user_query = user_query or query or kwargs.get("query")
#         board_id = idBoard
#         if not board_id and actual_user_query:
#             m = re.search(r"(?:BID|bid|Board ID|board id)\s*[:\-]?\s*([A-Za-z0-9_\-]+)", actual_user_query)
#             if m:
#                 board_id = m.group(1).strip()
#             else:
#                 m2 = re.search(r"\b([A-Za-z0-9_\-]{6,})\b", actual_user_query)
#                 if m2:
#                     board_id = m2.group(1).strip()

#         if not board_id:
#             raise ValueError("No board id provided and none could be parsed from the query. Provide idBoard or include 'BID: <id>' in the query.")

#         # ensure toolset exists (same behavior as your previous code)
#         if not hasattr(self, "toolset") or self.toolset is None:
#             self.toolset = ComposioToolSet(api_key=composio_api_key)

#         # Inline helper behavior: flatten arbitrary nested shapes into list of dicts (stack-based)
#         def _flatten_to_dicts(obj) -> List[Dict[str, Any]]:
#             results: List[Dict[str, Any]] = []
#             stack = [obj]
#             while stack:
#                 item = stack.pop()
#                 if item is None:
#                     continue
#                 if isinstance(item, dict):
#                     results.append(item)
#                     continue
#                 if isinstance(item, (list, tuple)):
#                     # push children to stack for processing
#                     for sub in item:
#                         stack.append(sub)
#                     continue
#                 # ignore primitives
#                 continue
#             return results

#         # Safe executor wrapper inline: execute action and return raw result or None (no extra function)
#         def _exec_action_safe(params: Dict[str, Any], action_name: str):
#             try:
#                 return self.toolset.execute_action(params=params, action=action_name)
#             except Exception as e:
#                 # keep behavior consistent with prior code: print warnings and continue
#                 print(f"[WARN] {action_name} failed for board {board_id}: {e}")
#                 return None

#         # 1) Fetch lists
#         lists_details: List[Dict[str, Any]] = []
#         lists_resp = _exec_action_safe({"idBoard": board_id}, "TRELLO_GET_BOARDS_LISTS_BY_ID_BOARD")
#         try:
#             lists_data = lists_resp.get("data", {}) if isinstance(lists_resp, dict) else lists_resp
#             raw_lists = lists_data.get("details") if isinstance(lists_data, dict) and "details" in lists_data else (
#                         lists_data.get("items") if isinstance(lists_data, dict) and "items" in lists_data else lists_data)
#             lists_details = _flatten_to_dicts(raw_lists)
#         except Exception:
#             lists_details = []

#         # try to extract board name from lists response
#         board_name = None
#         try:
#             if isinstance(lists_resp, dict):
#                 candidate = (lists_resp.get("data") or {}).get("board") or lists_resp.get("board") or (lists_resp.get("data") or {}).get("name")
#                 if isinstance(candidate, dict):
#                     board_name = candidate.get("name") or board_name
#                 elif isinstance(candidate, str):
#                     board_name = candidate or board_name
#         except Exception:
#             pass

#         # 2) Fetch members
#         members_map: Dict[str, Dict[str, Any]] = {}
#         members_resp = _exec_action_safe({"idBoard": board_id}, "TRELLO_GET_BOARDS_MEMBERS_BY_ID_BOARD")
#         try:
#             mr = members_resp.get("data", {}) if isinstance(members_resp, dict) else members_resp
#             raw_members = mr.get("details") if isinstance(mr, dict) and "details" in mr else (mr.get("items") if isinstance(mr, dict) and "items" in mr else mr)
#             members_list = _flatten_to_dicts(raw_members)
#             for m in members_list:
#                 mid = None
#                 if isinstance(m, dict):
#                     mid = m.get("id") or m.get("memberID") or m.get("idMember")
#                 if not mid:
#                     continue
#                 members_map[mid] = {
#                     "memberID": mid,
#                     "name": m.get("fullName") or m.get("name") or m.get("username") or m.get("displayName"),
#                     "permissions": m.get("permissions") or None,
#                     "_raw": m
#                 }
#         except Exception:
#             members_map = {}

#         # 3) Prefetch all board cards as fallback
#         all_board_cards_by_list: Dict[str, List[Dict[str, Any]]] = {}
#         cards_board_resp = _exec_action_safe({"idBoard": board_id}, "TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD")
#         try:
#             cbd = cards_board_resp.get("data", {}) if isinstance(cards_board_resp, dict) else cards_board_resp
#             raw_cards = cbd.get("details") if isinstance(cbd, dict) and "details" in cbd else (cbd.get("items") if isinstance(cbd, dict) and "items" in cbd else cbd)
#             cards_list = _flatten_to_dicts(raw_cards)
#             for card in cards_list:
#                 if not isinstance(card, dict):
#                     continue
#                 lid = card.get("idList") or card.get("id_list") or card.get("listID")
#                 if not lid:
#                     continue
#                 all_board_cards_by_list.setdefault(lid, []).append(card)
#             # fallback board name from cards response
#             if board_name is None and isinstance(cbd, dict):
#                 bname = (cbd.get("board") or {}).get("name") if cbd.get("board") else None
#                 if isinstance(bname, str) and bname:
#                     board_name = bname
#         except Exception:
#             all_board_cards_by_list = {}

#         # inline function to fetch actions for a given card id (no top-level helper)
#         def _fetch_actions_for_card(card_id: str) -> List[Dict[str, Any]]:
#             acts_resp = _exec_action_safe({"idCard": card_id}, "TRELLO_GET_CARDS_ACTIONS_BY_ID_CARD")
#             if not acts_resp:
#                 return []
#             ar = acts_resp.get("data", {}) if isinstance(acts_resp, dict) else acts_resp
#             raw_actions = ar.get("details") if isinstance(ar, dict) and "details" in ar else (ar.get("items") if isinstance(ar, dict) and "items" in ar else ar)
#             return _flatten_to_dicts(raw_actions)

#         # Build normalized board structure inline
#         normalized_board: Dict[str, Any] = {"idBoard": board_id, "name": board_name, "lists": []}

#         if not lists_details and all_board_cards_by_list:
#             # create pseudo lists from grouped cards
#             for lid, cards in all_board_cards_by_list.items():
#                 list_obj = {"listID": lid, "title": f"List {lid}", "cards": []}
#                 for card in cards:
#                     if not isinstance(card, dict):
#                         continue
#                     card_id = card.get("id") or card.get("idCard") or card.get("cardID")
#                     card_name = card.get("name") or card.get("title") or "<unnamed card>"
#                     card_desc = card.get("desc") or card.get("description") or ""
#                     card_due = card.get("due") or card.get("deadline") or None

#                     # members attached to the card (normalize)
#                     member_ids_raw = card.get("idMembers") or card.get("members") or card.get("memberIDs") or []
#                     normalized_member_ids: List[str] = []
#                     if isinstance(member_ids_raw, list):
#                         for m in member_ids_raw:
#                             if isinstance(m, dict):
#                                 mid = m.get("id") or m.get("memberID")
#                                 if mid:
#                                     normalized_member_ids.append(mid)
#                             elif isinstance(m, str):
#                                 normalized_member_ids.append(m)
#                     elif isinstance(member_ids_raw, str):
#                         normalized_member_ids.append(member_ids_raw)

#                     members_block: List[Dict[str, Any]] = []
#                     for mid in normalized_member_ids:
#                         mm = members_map.get(mid, {})
#                         members_block.append({"memberID": mid, "name": mm.get("name") or "<unknown>"})

#                     list_obj["cards"].append({
#                         "id": card_id,
#                         "name": card_name,
#                         "description": card_desc,
#                         "deadline": card_due,
#                         "members": members_block
#                     })
#                 normalized_board["lists"].append(list_obj)
#             # format inline and return
#             # build output lines
#             out_lines: List[str] = []
#             out_lines.append(f"1) Board: {normalized_board.get('name') or '<unnamed board>'} (ID: `{normalized_board.get('idBoard')}`)")
#             out_lines.append("")
#             out_lines.append("2) Lists & Cards")
#             out_lines.append("")
#             lists = normalized_board.get("lists") or []
#             if not lists:
#                 out_lines.append("  - (no lists detected in input)")
#                 return "\n".join(out_lines)
#             for li, lst in enumerate(lists, start=1):
#                 list_id = lst.get("listID") or "<no-id>"
#                 list_name = lst.get("title") or "<unnamed list>"
#                 out_lines.append(f"- {li}. {list_name} (List ID: `{list_id}`)")
#                 cards = lst.get("cards") or []
#                 if not cards:
#                     out_lines.append("    - (no cards in this list)")
#                     out_lines.append("")
#                     continue
#                 for ci, card in enumerate(cards, start=1):
#                     card_id = card.get("id") or "<no-id>"
#                     card_name = card.get("name") or "<unnamed card>"
#                     out_lines.append(f"    - {li}.{ci} Card: {card_name} (ID: `{card_id}`)")
#                     desc = card.get("description") or card.get("desc") or "<none>"
#                     if isinstance(desc, str) and len(desc) > 500:
#                         desc = desc[:500] + "... (truncated)"
#                     out_lines.append(f"        - Description: {desc}")
#                     deadline = card.get("deadline") or card.get("due") or "<none>"
#                     out_lines.append(f"        - Deadline: {deadline}")
#                     members_block = card.get("members") or []
#                     member_text = "<none>"
#                     if isinstance(members_block, list) and members_block:
#                         members_display = []
#                         for mb in members_block:
#                             if isinstance(mb, dict):
#                                 mname = mb.get("name") or "<unknown>"
#                                 mid = mb.get("memberID") or mb.get("memberId") or mb.get("id") or "<no-id>"
#                                 members_display.append(f"{mname} (ID: `{mid}`)")
#                             elif isinstance(mb, str):
#                                 members_display.append(mb)
#                         member_text = ", ".join(members_display) if members_display else "<none>"
#                     out_lines.append(f"        - Members: {member_text}")
#                     out_lines.append("")
#             return "\n".join(out_lines)

#         # otherwise iterate lists_details and populate cards
#         for lst in lists_details:
#             if not isinstance(lst, dict):
#                 continue
#             list_id = lst.get("id") or lst.get("idList") or lst.get("listID") or "<no-id>"
#             list_name = lst.get("name") or lst.get("title") or lst.get("listName") or "<unnamed list>"
#             list_obj: Dict[str, Any] = {"listID": list_id, "title": list_name, "cards": []}

#             # attempt a list-specific card fetch (defensive)
#             resp_cards = _exec_action_safe({"idList": list_id}, "TRELLO_GET_LISTS_CARDS_BY_ID_LIST") if list_id else None
#             cards_for_list = []
#             try:
#                 if isinstance(resp_cards, dict):
#                     rc = resp_cards.get("data", {}) if isinstance(resp_cards, dict) else resp_cards
#                     raw_cards_for_list = rc.get("details") if isinstance(rc, dict) and "details" in rc else (rc.get("items") if isinstance(rc, dict) and "items" in rc else rc)
#                 else:
#                     raw_cards_for_list = resp_cards
#                 cards_for_list = _flatten_to_dicts(raw_cards_for_list)
#             except Exception:
#                 cards_for_list = all_board_cards_by_list.get(list_id, []) or []

#             if not cards_for_list:
#                 cards_for_list = all_board_cards_by_list.get(list_id, []) or []

#             for card in cards_for_list:
#                 if not isinstance(card, dict):
#                     continue
#                 card_id = card.get("id") or card.get("idCard") or card.get("cardID")
#                 card_name = card.get("name") or card.get("title") or "<unnamed card>"
#                 card_desc = card.get("desc") or card.get("description") or ""
#                 card_due = card.get("due") or card.get("deadline") or None

#                 # normalize members attached to the card
#                 member_ids_raw = card.get("idMembers") or card.get("members") or card.get("memberIDs") or []
#                 normalized_member_ids: List[str] = []
#                 if isinstance(member_ids_raw, list):
#                     for m in member_ids_raw:
#                         if isinstance(m, dict):
#                             mid = m.get("id") or m.get("memberID")
#                             if mid:
#                                 normalized_member_ids.append(mid)
#                         elif isinstance(m, str):
#                             normalized_member_ids.append(m)
#                 elif isinstance(member_ids_raw, str):
#                     normalized_member_ids.append(member_ids_raw)

#                 members_block: List[Dict[str, Any]] = []
#                 for mid in normalized_member_ids:
#                     mm = members_map.get(mid, {})
#                     members_block.append({"memberID": mid, "name": mm.get("name") or "<unknown>"})

#                 # fetch actions/comments and add anonymous commenters to members_block if needed
#                 actions = _fetch_actions_for_card(card_id) if card_id else []
#                 overall_comments: List[Dict[str, Any]] = []
#                 for act in actions:
#                     if not isinstance(act, dict):
#                         continue
#                     atype = (act.get("type") or "").lower()
#                     if "comment" not in atype and atype != "commentcard":
#                         continue
#                     data = act.get("data") or {}
#                     text = None
#                     if isinstance(data, dict):
#                         text = data.get("text") or (data.get("comment") or {}).get("text")
#                     member_creator = act.get("memberCreator") or {}
#                     mid = member_creator.get("id") or member_creator.get("idMember")
#                     mname = member_creator.get("fullName") or member_creator.get("name") or member_creator.get("username")
#                     comment_obj = {"id": act.get("id"), "memberID": mid, "memberName": mname, "text": text, "date": act.get("date")}
#                     overall_comments.append(comment_obj)
#                 known_mids = {m["memberID"] for m in members_block if m.get("memberID")}
#                 for c in overall_comments:
#                     cmid = c.get("memberID")
#                     if cmid and cmid not in known_mids:
#                         members_block.append({"memberID": cmid, "name": c.get("memberName") or "<unknown>"})
#                         known_mids.add(cmid)

#                 list_obj["cards"].append({
#                     "id": card_id,
#                     "name": card_name,
#                     "description": card_desc,
#                     "deadline": card_due,
#                     "members": members_block
#                 })

#             normalized_board["lists"].append(list_obj)

#         # final inline formatting and return
#         out_lines: List[str] = []
#         out_lines.append(f"1) Board: {normalized_board.get('name') or '<unnamed board>'} (ID: `{normalized_board.get('idBoard')}`)")
#         out_lines.append("")
#         out_lines.append("2) Lists & Cards")
#         out_lines.append("")
#         lists = normalized_board.get("lists") or []
#         if not lists:
#             out_lines.append("  - (no lists detected in input)")
#             return "\n".join(out_lines)
#         for li, lst in enumerate(lists, start=1):
#             list_id = lst.get("listID") or "<no-id>"
#             list_name = lst.get("title") or "<unnamed list>"
#             out_lines.append(f"- {li}. {list_name} (List ID: `{list_id}`)")
#             cards = lst.get("cards") or []
#             if not cards:
#                 out_lines.append("    - (no cards in this list)")
#                 out_lines.append("")
#                 continue
#             for ci, card in enumerate(cards, start=1):
#                 card_id = card.get("id") or "<no-id>"
#                 card_name = card.get("name") or "<unnamed card>"
#                 out_lines.append(f"    - {li}.{ci} Card: {card_name} (ID: `{card_id}`)")
#                 desc = card.get("description") or card.get("desc") or "<none>"
#                 if isinstance(desc, str) and len(desc) > 500:
#                     desc = desc[:500] + "... (truncated)"
#                 out_lines.append(f"        - Description: {desc}")
#                 deadline = card.get("deadline") or card.get("due") or "<none>"
#                 out_lines.append(f"        - Deadline: {deadline}")
#                 members_block = card.get("members") or []
#                 member_text = "<none>"
#                 if isinstance(members_block, list) and members_block:
#                     members_display = []
#                     for mb in members_block:
#                         if isinstance(mb, dict):
#                             mname = mb.get("name") or "<unknown>"
#                             mid = mb.get("memberID") or mb.get("memberId") or mb.get("id") or "<no-id>"
#                             members_display.append(f"{mname} (ID: `{mid}`)")
#                         elif isinstance(mb, str):
#                             members_display.append(mb)
#                     member_text = ", ".join(members_display) if members_display else "<none>"
#                 out_lines.append(f"        - Members: {member_text}")
#                 out_lines.append("")
#         return "\n".join(out_lines)


# async def process_query(query: str, composio_api_key_param: str = None, gemini_api_key_param: str = None) -> Dict[str, Any]:
#     """
#     Process a query using sigmoyd trello operations.
#     Returns a dictionary with the result and any output.
    
#     Args:
#         query: The user query to process
#         composio_api_key_param: Optional Composio API key (uses env var if not provided)
#         gemini_api_key_param: Optional Gemini API key (uses env var if not provided)
    
#     Returns:
#         Dict with 'success', 'output', and 'error' keys
#     """
#     import io
#     import sys
#     from contextlib import redirect_stdout, redirect_stderr
    
#     # Use provided keys or fall back to environment variables
#     actual_composio_key = composio_api_key_param or composio_api_key
#     actual_gemini_key = gemini_api_key_param or gemini_api_key
    
#     output_lines = []
#     error_lines = []
    
#     try:
#         # Capture stdout and stderr
#         stdout_capture = io.StringIO()
#         stderr_capture = io.StringIO()
        
#         with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
#             # Initialize LLM if needed
#             llm_instance = get_llm(actual_gemini_key)
#             if not llm_instance:
#                 return {
#                     "success": False,
#                     "output": "",
#                     "error": "Gemini API key not provided or LLM initialization failed"
#                 }
            
#             # 1) classify high-level operations (Read/Write/Delete)
#             try:
#                 actions_cls = await get_all_actions(query=query, llm_instance=llm_instance)
#             except Exception as e:
#                 error_lines.append(f"[ERROR] High-level action classifier failed: {e}")
#                 actions_cls = None
            
#             output_lines.append(f"[HIGH-LEVEL ACTIONS]: {actions_cls}")
            
#             # Helper to test if the classifier requested a Read Operation
#             def classifier_has_read(actions):
#                 if not actions:
#                     return False
#                 if isinstance(actions, (list, tuple)):
#                     return "Read Operation" in actions
#                 return "Read Operation" in str(actions)
            
#             # If classifier result contains "Read Operation", proceed to resolve read tasks
#             if classifier_has_read(actions_cls):
#                 read_op = ReadOperation(composio_api_key=actual_composio_key, llm_instance=llm_instance)
                
#                 # 2) ask LLM to map query -> function(s) to run (get_task returns a string)
#                 try:
#                     read_task_result = await read_op.get_task(query)
#                 except Exception as e:
#                     error_lines.append(f"[ERROR] get_task failed: {e}")
#                     read_task_result = None
                
#                 output_lines.append(f"[READ TASK FUNCTIONS RAW]: {read_task_result}")
                
#                 # 3) Normalize the read_task_result into a python list of function names
#                 parsed_functions = []
#                 try:
#                     parsed = ast.literal_eval((read_task_result or "").strip())
#                     if isinstance(parsed, (list, tuple)):
#                         parsed_functions = [str(p) for p in parsed]
#                     else:
#                         parsed_functions = [str(parsed)]
#                 except Exception:
#                     # fallback: look for known function names in the returned string (preserves order)
#                     known = [
#                         "get_card_description",
#                         "get_list_content",
#                         "get_deadline",
#                         "get_all_deadlines",
#                         "get_board_content",
#                         "get_card_comment",
#                         "get_all_actions",
#                         "get_checklist",
#                     ]
#                     lower = (read_task_result or "").lower()
#                     for fn in known:
#                         if fn.lower() in lower:
#                             parsed_functions.append(fn)
                
#                 output_lines.append(f"[PARSED FUNCTIONS]: {parsed_functions}")
                
#                 # If nothing parsed, exit early
#                 if not parsed_functions:
#                     output_lines.append("[WARN] No functions parsed from LLM output. Aborting.")
#                     return {
#                         "success": False,
#                         "output": "\n".join(output_lines),
#                         "error": "No functions could be parsed from the query"
#                     }
                
#                 # Determine if we need a board_id for any requested function
#                 need_board = any(
#                     fn in parsed_functions
#                     for fn in [
#                         "get_list_content",
#                         "get_board_content",
#                         "get_card_description",
#                         "get_deadline",
#                         "get_all_deadlines",
#                         "get_card_comment",
#                         "get_all_actions",
#                         "get_checklist",
#                     ]
#                 )
#                 board_id = None
#                 if need_board:
#                     try:
#                         board_id = await read_op.get_board_id(query)
#                         output_lines.append(f"[INFO] Resolved board_id: {board_id}")
#                     except Exception as e:
#                         error_lines.append(f"[ERROR] get_board_id failed: {e}")
#                         board_id = None
                
#                 # Collect all results
#                 results = {}
                
#                 # Prioritize get_all_actions / get_board_content if requested
#                 if "get_all_actions" in parsed_functions or "get_board_content" in parsed_functions:
#                     if not board_id:
#                         output_lines.append("[WARN] get_all_actions/get_board_content requested but board_id not found. Skipping.")
#                     else:
#                         output_lines.append(f"[RUNNING] get_all_actions for board {board_id} ...")
#                         try:
#                             snapshot = await read_op.get_all_actions(board_id)
#                             results["get_all_actions"] = snapshot
#                             output_lines.append(f"[get_all_actions RESULT]: Success")
#                         except Exception as e:
#                             error_lines.append(f"[ERROR] get_all_actions failed: {e}")
                
#                 # Prioritize get_checklist if requested
#                 if "get_checklist" in parsed_functions:
#                     if not board_id:
#                         output_lines.append("[WARN] get_checklist requested but board_id not found. Skipping.")
#                     else:
#                         output_lines.append(f"[RUNNING] get_checklist for board {board_id} ...")
#                         try:
#                             checklist = await read_op.get_checklist(board_id, query)
#                             results["get_checklist"] = checklist
#                             output_lines.append(f"[get_checklist RESULT]: Success")
                            
#                             # Extract LLM summary if present
#                             if isinstance(checklist, dict):
#                                 llm_summary = checklist.get("llm_summary")
#                                 if llm_summary:
#                                     output_lines.append(f"\n[LLM Summary]\n{llm_summary}")
#                         except Exception as e:
#                             error_lines.append(f"[ERROR] get_checklist failed: {e}")
                
#                 # Continue executing other parsed functions
#                 for fn in parsed_functions:
#                     if fn in ("get_all_actions", "get_board_content", "get_checklist"):
#                         continue
                    
#                     output_lines.append(f"[RUNNING] {fn} ...")
#                     try:
#                         if fn == "get_list_content":
#                             if not board_id:
#                                 output_lines.append("[WARN] get_list_content requested but board_id not found. Skipping.")
#                                 continue
#                             res = await read_op.get_list_content(board_id, query)
#                             results[fn] = res
#                             output_lines.append(f"[{fn} RESULT]: Success")
                            
#                         elif fn == "get_card_description":
#                             if not board_id:
#                                 output_lines.append("[WARN] get_card_description requested but board_id not found. Skipping.")
#                                 continue
#                             res = await read_op.get_card_description(board_id, query)
#                             results[fn] = res
#                             output_lines.append(f"[{fn} RESULT]: Success")
                            
#                         elif fn in ("get_deadline", "get_all_deadlines"):
#                             if not board_id:
#                                 output_lines.append(f"[WARN] {fn} requested but board_id not found. Skipping.")
#                                 continue
#                             if fn == "get_deadline":
#                                 res = await read_op.get_deadline(board_id, query)
#                             else:
#                                 res = await read_op.get_all_deadlines(board_id, query)
#                             results[fn] = res
#                             output_lines.append(f"[{fn} RESULT]: Success")
                            
#                         elif fn == "get_card_comment":
#                             if not board_id:
#                                 output_lines.append("[WARN] get_card_comment requested but board_id not found. Skipping.")
#                                 continue
#                             res = await read_op.get_card_comment(board_id, query)
#                             results[fn] = res
#                             output_lines.append(f"[{fn} RESULT]: Success")
                            
#                         else:
#                             output_lines.append(f"[WARN] Unknown function requested by LLM: {fn}")
                            
#                     except Exception as e:
#                         error_lines.append(f"[ERROR] {fn} failed: {e}")
                
#                 # Format final output - clean, user-friendly format
#                 final_output = ""
                
#                 if results:
#                     # Format results in a clean, readable way
#                     for key, value in results.items():
#                         if key == "get_list_content":
#                             # Format tasks from list content
#                             if isinstance(value, dict):
#                                 tasks = value.get("tasks", [])
#                                 list_name = value.get("list_name", "List")
                                
#                                 if tasks:
#                                     final_output += f"📋 Tasks from '{list_name}':\n\n"
#                                     # Display all tasks in a simple numbered list
#                                     for i, task_name in enumerate(tasks, 1):
#                                         final_output += f"{i}. {task_name}\n"
#                                 else:
#                                     final_output += f"No tasks found in '{list_name}'.\n"
#                             elif isinstance(value, str):
#                                 # Fallback: if it's still a string (old format)
#                                 final_output += value
                        
#                         elif key == "get_checklist":
#                             # Format checklist items from board
#                             if isinstance(value, dict):
#                                 llm_summary = value.get("llm_summary", "")
#                                 if llm_summary:
#                                     final_output += llm_summary + "\n"
#                                 else:
#                                     # Try to extract from results
#                                     results_data = value.get("results", {})
#                                     all_items = []
#                                     for card_id, card_data in results_data.items():
#                                         if isinstance(card_data, dict):
#                                             tasks = card_data.get("tasks", [])
#                                             for task in tasks:
#                                                 if isinstance(task, dict):
#                                                     all_items.append(task.get("text", ""))
#                                     if all_items:
#                                         final_output += "📋 Tasks:\n\n"
#                                         for i, item in enumerate(all_items, 1):
#                                             final_output += f"{i}. {item}\n"
#                                     else:
#                                         final_output += json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n"
#                             else:
#                                 final_output += str(value) + "\n"
                        
#                         elif key == "get_all_actions" or key == "get_board_content":
#                             # Format board content
#                             if isinstance(value, str):
#                                 final_output += value + "\n"
#                             elif isinstance(value, dict):
#                                 lists = value.get("lists", [])
#                                 if lists:
#                                     final_output += "📋 Board Content:\n\n"
#                                     for lst in lists:
#                                         list_name = lst.get("title", lst.get("name", "Unnamed List"))
#                                         cards = lst.get("cards", [])
#                                         if cards:
#                                             final_output += f"\n📌 {list_name}:\n"
#                                             for card in cards:
#                                                 card_name = card.get("name", "Unnamed Card")
#                                                 final_output += f"  • {card_name}\n"
#                             else:
#                                 final_output += json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n"
                        
#                         else:
#                             # For other result types, format cleanly
#                             if isinstance(value, (dict, list)):
#                                 try:
#                                     final_output += json.dumps(value, ensure_ascii=False, indent=2, default=str) + "\n"
#                                 except:
#                                     final_output += str(value) + "\n"
#                             else:
#                                 final_output += str(value) + "\n"
                
#                 # If no formatted output was created, show a message
#                 if not final_output.strip():
#                     final_output = "No results to display. Please check your query and try again."
                
#                 return {
#                     "success": True,
#                     "output": final_output,
#                     "results": results,
#                     "errors": "\n".join(error_lines) if error_lines else None
#                 }
#             else:
#                 output_lines.append(f"[INFO] Query did not request Read operations. High-level actions: {actions_cls}")
#                 return {
#                     "success": False,
#                     "output": "\n".join(output_lines),
#                     "error": "Query did not request Read operations. Write/Delete operations are not yet supported via this endpoint."
#                 }
        
#         # Get captured output
#         stdout_text = stdout_capture.getvalue()
#         stderr_text = stderr_capture.getvalue()
        
#         if stdout_text:
#             output_lines.append(stdout_text)
#         if stderr_text:
#             error_lines.append(stderr_text)
            
#     except Exception as e:
#         error_lines.append(f"[FATAL ERROR]: {str(e)}")
#         import traceback
#         error_lines.append(traceback.format_exc())
#         return {
#             "success": False,
#             "output": "\n".join(output_lines),
#             "error": "\n".join(error_lines)
#         }
    
#     return {
#         "success": True,
#         "output": "\n".join(output_lines),
#         "errors": "\n".join(error_lines) if error_lines else None
#     }


# #this main is just made for read operation
# if __name__ == "__main__":
#     query = "fetch the whole board content from board"

#     # 1) classify high-level operations (Read/Write/Delete)
#     try:
#         actions_cls = asyncio.run(get_all_actions(query=query))
#     except Exception as e:
#         print("[ERROR] High-level action classifier failed:", e)
#         actions_cls = None

#     print("[HIGH-LEVEL ACTIONS]:", actions_cls)

#     # Helper to test if the classifier requested a Read Operation
#     def classifier_has_read(actions):
#         if not actions:
#             return False
#         if isinstance(actions, (list, tuple)):
#             return "Read Operation" in actions
#         return "Read Operation" in str(actions)

#     # If classifier result contains "Read Operation", proceed to resolve read tasks
#     if classifier_has_read(actions_cls):
#         read_op = ReadOperation(composio_api_key=composio_api_key)

#         # 2) ask LLM to map query -> function(s) to run (get_task returns a string)
#         try:
#             read_task_result = asyncio.run(read_op.get_task(query))
#         except Exception as e:
#             print("[ERROR] get_task failed:", e)
#             read_task_result = None

#         print("[READ TASK FUNCTIONS RAW]:", read_task_result)

#         # 3) Normalize the read_task_result into a python list of function names
#         parsed_functions = []
#         try:
#             parsed = ast.literal_eval((read_task_result or "").strip())
#             if isinstance(parsed, (list, tuple)):
#                 parsed_functions = [str(p) for p in parsed]
#             else:
#                 parsed_functions = [str(parsed)]
#         except Exception:
#             # fallback: look for known function names in the returned string (preserves order)
#             known = [
#                 "get_card_description",
#                 "get_list_content",
#                 "get_deadline",
#                 "get_all_deadlines",
#                 "get_board_content",
#                 "get_card_comment",
#                 "get_all_actions",
#                 "get_checklist",
#             ]
#             lower = (read_task_result or "").lower()
#             for fn in known:
#                 if fn.lower() in lower:
#                     parsed_functions.append(fn)

#         print("[PARSED FUNCTIONS]:", parsed_functions)

#         # If nothing parsed, exit early
#         if not parsed_functions:
#             print("[WARN] No functions parsed from LLM output. Aborting.")
#         else:
#             # Determine if we need a board_id for any requested function
#             need_board = any(
#                 fn in parsed_functions
#                 for fn in [
#                     "get_list_content",
#                     "get_board_content",
#                     "get_card_description",
#                     "get_deadline",
#                     "get_all_deadlines",
#                     "get_card_comment",
#                     "get_all_actions",
#                     "get_checklist",
#                 ]
#             )
#             board_id = None
#             if need_board:
#                 try:
#                     board_id = asyncio.run(read_op.get_board_id(query))
#                     print("[INFO] Resolved board_id:", board_id)
#                 except Exception as e:
#                     print("[ERROR] get_board_id failed:", e)
#                     board_id = None

#             # Prioritize get_all_actions / get_board_content if requested
#             if "get_all_actions" in parsed_functions or "get_board_content" in parsed_functions:
#                 if not board_id:
#                     print("[WARN] get_all_actions/get_board_content requested but board_id not found. Skipping.")
#                 else:
#                     print(f"[RUNNING] get_all_actions for board {board_id} ...")
#                     try:
#                         snapshot = asyncio.run(read_op.get_all_actions(board_id))
#                         try:
#                             print("[get_all_actions RESULT]:")
#                             print(json.dumps(snapshot, ensure_ascii=False, indent=2))
#                         except Exception:
#                             print("[get_all_actions RESULT]: (non-serializable python object)")
#                             print(snapshot)

#                         out_fname = f"board_{board_id}_snapshot.json"
#                         try:
#                             with open(out_fname, "w", encoding="utf-8") as f:
#                                 json.dump(snapshot, f, ensure_ascii=False, indent=2)
#                             print(f"[INFO] Snapshot saved to {out_fname}")
#                         except Exception as e:
#                             print(f"[WARN] Failed to save snapshot to file: {e}")

#                     except Exception as e:
#                         print("[ERROR] get_all_actions failed:", e)

#             # Prioritize get_checklist if requested (run even if get_all_actions also requested)
#             if "get_checklist" in parsed_functions:
#                 if not board_id:
#                     print("[WARN] get_checklist requested but board_id not found. Skipping.")
#                 else:
#                     print(f"[RUNNING] get_checklist for board {board_id} ...")
#                     try:
#                         checklist = asyncio.run(read_op.get_checklist(board_id, query))
#                         # pretty print structured result
#                         try:
#                             print("[get_checklist RESULT]:")
#                             print(json.dumps(checklist, ensure_ascii=False, indent=2, default=str))
#                         except Exception:
#                             print("[get_checklist RESULT]: (non-serializable python object)")
#                             print(checklist)

#                         # show LLM summary if present (get_checklist returns dict with llm_summary)
#                         if isinstance(checklist, dict):
#                             llm_summary = checklist.get("llm_summary")
#                             if llm_summary:
#                                 print("\n[LLM Summary]\n")
#                                 print(llm_summary)

#                         out_fname = f"board_{board_id}_get_checklist.json"
#                         try:
#                             with open(out_fname, "w", encoding="utf-8") as f:
#                                 json.dump(checklist, f, ensure_ascii=False, indent=2, default=str)
#                             print(f"[INFO] Checklist saved to {out_fname}")
#                         except Exception as e:
#                             print(f"[WARN] Failed to save checklist to file: {e}")

#                     except Exception as e:
#                         print("[ERROR] get_checklist failed:", e)

#             # Continue executing other parsed functions (preserves original order)
#             for fn in parsed_functions:
#                 if fn in ("get_all_actions", "get_board_content", "get_checklist"):
#                     # already handled above (or intentionally skipped)
#                     continue

#                 print(f"[RUNNING] {fn} ...")
#                 try:
#                     if fn == "get_list_content":
#                         if not board_id:
#                             print("[WARN] get_list_content requested but board_id not found. Skipping.")
#                             continue
#                         res = asyncio.run(read_op.get_list_content(board_id, query))
#                         if isinstance(res, dict):
#                             print("[get_list_content RESULT]:")
#                             print(json.dumps(res, ensure_ascii=False, indent=2))
#                         else:
#                             print("[get_list_content RESULT]:", res)

#                     elif fn == "get_card_description":
#                         if not board_id:
#                             print("[WARN] get_card_description requested but board_id not found. Skipping.")
#                             continue
#                         res = asyncio.run(read_op.get_card_description(board_id, query))
#                         print(
#                             "[get_card_description RESULT]:",
#                             json.dumps(res, ensure_ascii=False, indent=2) if isinstance(res, (dict, list)) else res,
#                         )

#                     elif fn in ("get_deadline", "get_all_deadlines"):
#                         if not board_id:
#                             print(f"[WARN] {fn} requested but board_id not found. Skipping.")
#                             continue
#                         if fn == "get_deadline":
#                             res = asyncio.run(read_op.get_deadline(board_id, query))
#                             print(
#                                 "[get_deadline RESULT]:",
#                                 json.dumps(res, ensure_ascii=False, indent=2) if isinstance(res, (dict, list)) else res,
#                             )
#                         else:
#                             res = asyncio.run(read_op.get_all_deadlines(board_id, query))
#                             print(
#                                 "[get_all_deadlines RESULT]:",
#                                 json.dumps(res, ensure_ascii=False, indent=2) if isinstance(res, (dict, list)) else res,
#                             )

#                     elif fn == "get_card_comment":
#                         if not board_id:
#                             print("[WARN] get_card_comment requested but board_id not found. Skipping.")
#                             continue
#                         res = asyncio.run(read_op.get_card_comment(board_id, query))
#                         print(
#                             "[get_card_comment RESULT]:",
#                             json.dumps(res, ensure_ascii=False, indent=2) if isinstance(res, (dict, list)) else res,
#                         )

#                     else:
#                         print(f"[WARN] Unknown function requested by LLM: {fn}")

#                 except Exception as e:
#                     print(f"[ERROR] {fn} failed:", e)

#     else:
#         print("[INFO] Query did not request Read operations. High-level actions:", actions_cls)

