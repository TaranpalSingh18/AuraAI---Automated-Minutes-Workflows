"""
Composio authentication service - handles OAuth connections for Trello
"""
# import sys
# import os
# from pathlib import Path
# from typing import Optional, Dict, Any

# # Add Composio path if it exists (for local development)
# backend_dir = Path(__file__).parent
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
#                     if 'composio_auth' not in module_name:
#                         removed_modules[module_name] = sys.modules[module_name]
#                         del sys.modules[module_name]
                
#                 try:
#                     from plugins.langchain.composio_langchain.toolset import ComposioToolSet
#                 except ImportError as e:
#                     import_error_msg = f"Local composio path exists but import failed: {str(e)}"
#                     # Restore modules if import failed
#                     for module_name, module_obj in removed_modules.items():
#                         sys.modules[module_name] = module_obj

# # Try to import App (may not be available in all composio versions)
# try:
#     from composio import App
# except ImportError:
#     App = None

# # Try to import NoItemsFound
# try:
#     from composio.client.exceptions import NoItemsFound
# except ImportError:
#     # Fallback if NoItemsFound is not available
#     class NoItemsFound(Exception):
#         pass
from typing import Optional, Dict, Any
from composio.tools.toolset import ComposioToolSet
from composio.client.exceptions import NoItemsFound


def initiate_trello_connection(api_key: str, redirect_url: Optional[str] = None) -> Dict[str, Any]:
    """
    Initiate Trello OAuth connection via Composio
    
    Args:
        api_key: Composio API key
        redirect_url: Optional redirect URL for OAuth callback
        
    Returns:
        Dictionary with redirectUrl, connectedAccountId, and connectionStatus
    """
    if ComposioToolSet is None:
        error_detail = "ComposioToolSet is not available. "
        if composio_path.exists():
            error_detail += f"The local composio repository exists at {composio_path}, but ComposioToolSet could not be imported. "
        else:
            error_detail += f"The local composio repository is not found at {composio_path}. "
        error_detail += "Please ensure the Composio SDK is properly installed or the local repository is available."
        if import_error_msg:
            error_detail += f" Import error: {import_error_msg}"
        raise RuntimeError(error_detail)
    
    try:
        toolset = ComposioToolSet(api_key=api_key)
        
        # Trello uses OAUTH1
        connection_request = toolset.initiate_connection(
            app="trello",
            auth_scheme="OAUTH1",
            redirect_url=redirect_url,
        )
        
        return {
            "redirect_url": connection_request.redirectUrl,
            "connected_account_id": connection_request.connectedAccountId,
            "connection_status": connection_request.connectionStatus,
        }
    except Exception as e:
        # Provide more detailed error information
        error_msg = f"Failed to initiate Trello connection: {str(e)}"
        import traceback
        traceback.print_exc()  # Print full traceback for debugging
        raise RuntimeError(error_msg) from e


def disconnect_trello(api_key: str) -> Dict[str, Any]:
    """
    Disconnect Trello connection via Composio
    
    Args:
        api_key: Composio API key
        
    Returns:
        Dictionary with success status
    """
    if ComposioToolSet is None:
        error_detail = "ComposioToolSet is not available. "
        if composio_path.exists():
            error_detail += f"The local composio repository exists at {composio_path}, but ComposioToolSet could not be imported. "
        else:
            error_detail += f"The local composio repository is not found at {composio_path}. "
        error_detail += "Please ensure the Composio SDK is properly installed or the local repository is available."
        if import_error_msg:
            error_detail += f" Import error: {import_error_msg}"
        raise RuntimeError(error_detail)
    
    toolset = ComposioToolSet(api_key=api_key)
    entity = toolset.get_entity()
    
    try:
        connection = entity.get_connection(app="trello")
        # Delete the connection using the HTTP client directly
        toolset.client.http.delete(url=f"/api/v1/connectedAccounts/{connection.id}")
        
        return {
            "success": True,
            "message": "Trello disconnected successfully. You can now reconnect with write permissions."
        }
    except NoItemsFound:
        return {
            "success": False,
            "message": "Trello is not connected"
        }
    except Exception as e:
        return {
            "success": False,
            "message": f"Failed to disconnect Trello: {str(e)}"
        }


def check_trello_connection(api_key: str) -> Dict[str, Any]:
    """
    Check if Trello is already connected via Composio
    
    Args:
        api_key: Composio API key
        
    Returns:
        Dictionary with is_connected (bool) and connection details if connected
    """
    if ComposioToolSet is None:
        error_detail = "ComposioToolSet is not available. "
        if composio_path.exists():
            error_detail += f"The local composio repository exists at {composio_path}, but ComposioToolSet could not be imported. "
        else:
            error_detail += f"The local composio repository is not found at {composio_path}. "
        error_detail += "Please ensure the Composio SDK is properly installed or the local repository is available."
        if import_error_msg:
            error_detail += f" Import error: {import_error_msg}"
        raise RuntimeError(error_detail)
    
    toolset = ComposioToolSet(api_key=api_key)
    entity = toolset.get_entity()
    
    try:
        connection_details = entity.get_connection(app="trello")
        
        return {
            "is_connected": connection_details.status == "ACTIVE",
            "connection_id": connection_details.id,
            "status": connection_details.status,
            "app_unique_id": connection_details.appUniqueId,
        }
    except NoItemsFound:
        return {
            "is_connected": False,
            "connection_id": None,
            "status": None,
            "app_unique_id": None,
        }
    except Exception as e:
        return {
            "is_connected": False,
            "connection_id": None,
            "status": None,
            "app_unique_id": None,
            "error": str(e),
        }


def get_trello_boards(api_key: str) -> Dict[str, Any]:
    """
    Fetch all Trello boards for the authenticated user
    
    Args:
        api_key: Composio API key
        
    Returns:
        Dictionary with boards list (id, name, url, etc.)
    """
    if ComposioToolSet is None:
        error_detail = "ComposioToolSet is not available. "
        if composio_path.exists():
            error_detail += f"The local composio repository exists at {composio_path}, but ComposioToolSet could not be imported. "
        else:
            error_detail += f"The local composio repository is not found at {composio_path}. "
        error_detail += "Please ensure the Composio SDK is properly installed or the local repository is available."
        if import_error_msg:
            error_detail += f" Import error: {import_error_msg}"
        raise RuntimeError(error_detail)
    
    toolset = ComposioToolSet(api_key=api_key)
    entity = toolset.get_entity()
    
    # Check if Trello is connected first
    try:
        connection = entity.get_connection(app="trello")
        if connection.status != "ACTIVE":
            raise RuntimeError("Trello is not connected. Please connect Trello first.")
    except NoItemsFound:
        raise RuntimeError("Trello is not connected. Please connect Trello first.")
    
    try:
        # Use TRELLO_GET_MEMBERS_BOARDS_BY_ID_MEMBER action to get boards
        # First, we need to get the member ID - typically "me" works
        # Try executing the action to get boards
        result = toolset.execute_action(
            action="TRELLO_GET_MEMBERS_BOARDS_BY_ID_MEMBER",
            params={"id": "me"},
            entity_id=entity.id
        )
        
        # Extract boards from result
        boards = []
        if isinstance(result, dict):
            # Result might be in different formats
            if "data" in result and isinstance(result["data"], list):
                boards = result["data"]
            elif isinstance(result, list):
                boards = result
            elif "boards" in result:
                boards = result["boards"]
        
        # Format boards for response
        formatted_boards = []
        for board in boards:
            if isinstance(board, dict):
                formatted_boards.append({
                    "id": board.get("id", ""),
                    "name": board.get("name", ""),
                    "url": board.get("url", ""),
                    "closed": board.get("closed", False),
                    "organization": board.get("organization", {}).get("name", "") if isinstance(board.get("organization"), dict) else ""
                })
        
        return {
            "boards": formatted_boards,
            "count": len(formatted_boards)
        }
    except Exception as e:
        # If the action doesn't work, try alternative approach
        # Some Trello APIs use different action names
        try:
            # Try using the connected account directly via API
            # This is a fallback - may need adjustment based on actual Composio response format
            return {
                "boards": [],
                "count": 0,
                "error": f"Failed to fetch boards: {str(e)}",
                "note": "Please manually enter your board ID from Trello"
            }
        except Exception as e2:
            raise RuntimeError(f"Failed to fetch Trello boards: {str(e2)}")


def get_trello_cards(api_key: str, board_id: str) -> Dict[str, Any]:
    """
    Fetch all cards from a Trello board with full details
    Based on pattern from trello.py - just fetch cards directly
    
    Args:
        api_key: Composio API key
        board_id: Trello board ID
        
    Returns:
        Dictionary with cards and their full details
    """
    if ComposioToolSet is None:
        error_detail = "ComposioToolSet is not available. "
        if composio_path.exists():
            error_detail += f"The local composio repository exists at {composio_path}, but ComposioToolSet could not be imported. "
        else:
            error_detail += f"The local composio repository is not found at {composio_path}. "
        error_detail += "Please ensure the Composio SDK is properly installed or the local repository is available."
        if import_error_msg:
            error_detail += f" Import error: {import_error_msg}"
        raise RuntimeError(error_detail)
    
    toolset = ComposioToolSet(api_key=api_key)
    entity = toolset.get_entity()
    
    # Check if Trello is connected first
    try:
        connection = entity.get_connection(app="trello")
        if connection.status != "ACTIVE":
            raise RuntimeError("Trello is not connected. Please connect Trello first.")
    except NoItemsFound:
        raise RuntimeError("Trello is not connected. Please connect Trello first.")
    
    try:
        # Get all cards on the board - following trello.py pattern
        # Try with entity_id first (like get_trello_boards does)
        print(f"DEBUG: Fetching cards for board_id: {board_id}")
        cards_result = None
        last_error = None
        
        # Try multiple parameter variations
        param_variations = [
            {"idBoard": board_id},
            {"id": board_id},
            {"board_id": board_id},
        ]
        
        for params in param_variations:
            try:
                print(f"DEBUG: Trying params: {params}")
                cards_result = toolset.execute_action(
                    action="TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD",
                    params=params,
                    entity_id=entity.id
                )
                # Check if we got actual data
                if isinstance(cards_result, dict):
                    data = cards_result.get("data", {})
                    if isinstance(data, list) and len(data) > 0:
                        print(f"DEBUG: Successfully got cards with params: {params}")
                        break
                    elif isinstance(data, dict) and len(data) > 0:
                        # Check if data has cards
                        if "cards" in data or any(isinstance(v, list) and len(v) > 0 for v in data.values()):
                            print(f"DEBUG: Successfully got cards with params: {params}")
                            break
                elif isinstance(cards_result, list) and len(cards_result) > 0:
                    print(f"DEBUG: Successfully got cards with params: {params}")
                    break
            except Exception as e1:
                last_error = e1
                print(f"DEBUG: Failed with params {params}: {e1}")
                continue
        
        # If all variations failed, try without entity_id
        if cards_result is None or (isinstance(cards_result, dict) and isinstance(cards_result.get("data"), dict) and len(cards_result.get("data", {})) == 0):
            print(f"DEBUG: Trying without entity_id...")
            try:
                cards_result = toolset.execute_action(
                    action="TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD",
                    params={"idBoard": board_id}
                )
            except Exception as e2:
                if last_error:
                    raise last_error
                raise e2
        
        # Debug: Print the raw response structure
        print(f"DEBUG: Raw cards_result type: {type(cards_result)}")
        if isinstance(cards_result, dict):
            print(f"DEBUG: cards_result keys: {list(cards_result.keys())}")
            # Check for error message (note: Composio uses "successfull" typo)
            if "error" in cards_result and cards_result["error"]:
                print(f"DEBUG: Error in response: {cards_result['error']}")
            if "successfull" in cards_result:
                print(f"DEBUG: successfull value: {cards_result['successfull']}")
            if "data" in cards_result:
                print(f"DEBUG: data type: {type(cards_result['data'])}")
                if isinstance(cards_result["data"], dict):
                    print(f"DEBUG: data keys: {list(cards_result['data'].keys())}")
                    print(f"DEBUG: data content: {cards_result['data']}")
                elif isinstance(cards_result["data"], list):
                    print(f"DEBUG: data is a list with {len(cards_result['data'])} items")
        elif isinstance(cards_result, list):
            print(f"DEBUG: cards_result is a list with {len(cards_result)} items")
            if len(cards_result) > 0:
                print(f"DEBUG: First item type: {type(cards_result[0])}, keys: {list(cards_result[0].keys()) if isinstance(cards_result[0], dict) else 'N/A'}")
        
        # Parse cards - following trello.py pattern (line 82-90)
        all_cards = []
        if isinstance(cards_result, list):
            all_cards = cards_result
        elif isinstance(cards_result, dict):
            # Check for error message first
            if "error" in cards_result and cards_result["error"]:
                error_msg = cards_result["error"]
                print(f"DEBUG: Error in response: {error_msg}")
                # Don't raise error yet - might still have data
            
            # Check for successful/error flags (note: Composio uses "successfull" typo)
            if cards_result.get("successfull") is False or cards_result.get("successful") is False:
                error_msg = cards_result.get("error", "Unknown error")
                print(f"DEBUG: Action returned unsuccessful: {error_msg}")
                raise RuntimeError(f"Trello API error: {error_msg}")
            
            # Check if data is actually a list (sometimes it is)
            if "data" in cards_result:
                data = cards_result["data"]
                if isinstance(data, list):
                    all_cards = data
                    print(f"DEBUG: Found cards directly in data (list)")
                elif isinstance(data, dict):
                    if "cards" in data:
                        all_cards = data["cards"]
                        print(f"DEBUG: Found cards in data.cards")
                    elif len(data) == 0:
                        # Empty dict - might mean no cards or wrong response format
                        print(f"DEBUG: data dict is empty - checking if we need different parameters")
                        # Try alternative: maybe the response format is different
                        # Check if error suggests something
                        if "error" in cards_result:
                            print(f"DEBUG: Response has error but data is empty: {cards_result.get('error')}")
                    else:
                        # Check if data itself contains list of cards in any key
                        for key, value in data.items():
                            if isinstance(value, list) and len(value) > 0:
                                if isinstance(value[0], dict) and "id" in value[0] and ("name" in value[0] or "idList" in value[0]):
                                    all_cards = value
                                    print(f"DEBUG: Found cards in data.{key}")
                                    break
            
            # Also check top-level keys
            if len(all_cards) == 0:
                if "cards" in cards_result:
                    all_cards = cards_result["cards"]
                    print(f"DEBUG: Found cards in top-level 'cards' key")
                elif "id" in cards_result and "name" in cards_result:
                    # Single card response
                    all_cards = [cards_result]
                    print(f"DEBUG: Single card response")
                else:
                    # Last resort: check all keys for lists that might contain cards
                    print(f"DEBUG: Checking all keys for card-like lists...")
                    for key, value in cards_result.items():
                        if isinstance(value, list) and len(value) > 0:
                            if isinstance(value[0], dict):
                                # Check if it looks like a card (has id and name/idList)
                                if "id" in value[0] and ("name" in value[0] or "idList" in value[0]):
                                    all_cards = value
                                    print(f"DEBUG: Found cards in top-level key '{key}'")
                                    break
        
        print(f"DEBUG: Parsed {len(all_cards)} cards from Trello API for board {board_id}")
        
        # If no cards found, try alternative approach: get lists first, then cards from each list
        if len(all_cards) == 0:
            print(f"DEBUG: No cards found with direct call, trying to get cards via lists...")
            try:
                # Get all lists on the board
                lists_result = toolset.execute_action(
                    action="TRELLO_GET_BOARDS_LISTS_BY_ID_BOARD",
                    params={"idBoard": board_id},
                    entity_id=entity.id
                )
                
                print(f"DEBUG: Lists result type: {type(lists_result)}")
                if isinstance(lists_result, dict):
                    lists_data = lists_result.get("data", [])
                    if isinstance(lists_data, dict):
                        # Try to extract lists from dict
                        for key, value in lists_data.items():
                            if isinstance(value, list):
                                lists_data = value
                                break
                elif isinstance(lists_result, list):
                    lists_data = lists_result
                else:
                    lists_data = []
                
                print(f"DEBUG: Found {len(lists_data) if isinstance(lists_data, list) else 0} lists")
                
                # Get cards from each list
                if isinstance(lists_data, list):
                    for list_item in lists_data:
                        if not isinstance(list_item, dict):
                            continue
                        list_id = list_item.get("id", "")
                        if not list_id:
                            continue
                        
                        try:
                            # Get cards from this list
                            list_cards_result = toolset.execute_action(
                                action="TRELLO_GET_LISTS_CARDS_BY_ID_LIST",
                                params={"idList": list_id},
                                entity_id=entity.id
                            )
                            
                            # Parse cards from list
                            list_cards = []
                            if isinstance(list_cards_result, dict):
                                list_data = list_cards_result.get("data", [])
                                if isinstance(list_data, list):
                                    list_cards = list_data
                                elif isinstance(list_data, dict) and "cards" in list_data:
                                    list_cards = list_data["cards"]
                            elif isinstance(list_cards_result, list):
                                list_cards = list_cards_result
                            
                            print(f"DEBUG: Found {len(list_cards)} cards in list {list_id}")
                            all_cards.extend(list_cards)
                        except Exception as e:
                            print(f"DEBUG: Failed to get cards from list {list_id}: {e}")
                            continue
                
                print(f"DEBUG: Total cards found via lists: {len(all_cards)}")
            except Exception as e:
                print(f"DEBUG: Failed to get cards via lists: {e}")
        
        # Format cards with all available information
        formatted_cards = []
        for card in all_cards:
            if not isinstance(card, dict):
                continue
            
            card_id = card.get("id", "")
            if not card_id:
                continue
            
            list_id = card.get("idList", "")
            
            # Get comments count from badges if available
            badges = card.get("badges", {})
            comments_count = 0
            checklists_count = 0
            if isinstance(badges, dict):
                comments_count = badges.get("comments", 0)
                checklists_count = badges.get("checkItems", 0)
            
            formatted_cards.append({
                "id": card_id,
                "name": card.get("name", ""),
                "desc": card.get("desc", ""),
                "closed": card.get("closed", False),
                "shortUrl": card.get("shortUrl", ""),
                "url": card.get("url", ""),
                "dateLastActivity": card.get("dateLastActivity", ""),
                "due": card.get("due", ""),
                "dueComplete": card.get("dueComplete", False),
                "list_id": list_id,
                "list_name": card.get("list", {}).get("name", "") if isinstance(card.get("list"), dict) else "",
                "comments_count": comments_count,
                "badges": card.get("badges", {}),
                "labels": card.get("labels", []),
                "members": card.get("idMembers", []),
                "checklists_count": checklists_count
            })
        
        return {
            "cards": formatted_cards,
            "count": len(formatted_cards)
        }
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"ERROR in get_trello_cards: {str(e)}")
        print(f"Traceback: {error_trace}")
        raise RuntimeError(f"Failed to fetch Trello cards: {str(e)}")


# import sys
# import os
# sys.path.insert(0, r"D:/minor/Model/composio/python")
# from composio import Action, App  #
# from composio.client.exceptions import NoItemsFound
# from plugins.langchain.composio_langchain.toolset import ComposioToolSet

# import requests

# # os.environ["COMPOSIO_API_KEY"] =  os.getenv("COMPOSIO_API_KEY")

# def create_connection_oauth2(app_name,api_key, auth_scheme="OAUTH2"):
#     toolset = ComposioToolSet(api_key=api_key)
#     connection_request = toolset.initiate_connection(
#         app=app_name, # user comes here after oauth flow
#         # entity_id=entity_id,
#         auth_scheme=auth_scheme,
#     )
#     print(connection_request.connectedAccountId,connection_request.connectionStatus)
#     # Redirect user to the redirect url so they complete the oauth flow
#     print(connection_request.redirectUrl)
#     return connection_request.redirectUrl




# def check_connection( app_name, api_key):
#     toolset = ComposioToolSet(api_key=api_key)

#     # Filter based on entity id
#     entity = toolset.get_entity()  # fill entity id here

#     try:
#         # Filters based on app name
#         connection_details = entity.get_connection(app=app_name) 

#         print(connection_details)
#         if connection_details.status == "ACTIVE":
#             return True
#         else:
#             return False

#     except NoItemsFound as e:
#         print("No connected account found")
#         return False


# # Wrapper functions for composio_routes.py compatibility
# from typing import Optional, Dict, Any

# def initiate_trello_connection(api_key: str, redirect_url: Optional[str] = None) -> Dict[str, Any]:
#     """
#     Initiate Trello OAuth connection via Composio
    
#     Args:
#         api_key: Composio API key
#         redirect_url: Optional redirect URL for OAuth callback
        
#     Returns:
#         Dictionary with redirectUrl, connectedAccountId, and connectionStatus
#     """
#     toolset = ComposioToolSet(api_key=api_key)
    
#     # Trello uses OAUTH1
#     connection_request = toolset.initiate_connection(
#         app="trello",
#         auth_scheme="OAUTH1",
#         redirect_url=redirect_url,
#     )
    
#     return {
#         "redirect_url": connection_request.redirectUrl,
#         "connected_account_id": connection_request.connectedAccountId,
#         "connection_status": connection_request.connectionStatus,
#     }


# def check_trello_connection(api_key: str) -> Dict[str, Any]:
#     """
#     Check if Trello is already connected via Composio
    
#     Args:
#         api_key: Composio API key
        
#     Returns:
#         Dictionary with is_connected (bool) and connection details if connected
#     """
#     toolset = ComposioToolSet(api_key=api_key)
#     entity = toolset.get_entity()
    
#     try:
#         connection_details = entity.get_connection(app="trello")
        
#         return {
#             "is_connected": connection_details.status == "ACTIVE",
#             "connection_id": connection_details.id,
#             "status": connection_details.status,
#             "app_unique_id": connection_details.appUniqueId,
#         }
#     except NoItemsFound:
#         return {
#             "is_connected": False,
#             "connection_id": None,
#             "status": None,
#             "app_unique_id": None,
#         }
#     except Exception as e:
#         return {
#             "is_connected": False,
#             "connection_id": None,
#             "status": None,
#             "app_unique_id": None,
#             "error": str(e),
#         }


# def disconnect_trello(api_key: str) -> Dict[str, Any]:
#     """
#     Disconnect Trello connection via Composio
    
#     Args:
#         api_key: Composio API key
        
#     Returns:
#         Dictionary with success status
#     """
#     toolset = ComposioToolSet(api_key=api_key)
#     entity = toolset.get_entity()
    
#     try:
#         connection = entity.get_connection(app="trello")
#         # Delete the connection using the HTTP client directly
#         toolset.client.http.delete(url=f"/api/v1/connectedAccounts/{connection.id}")
        
#         return {
#             "success": True,
#             "message": "Trello disconnected successfully. You can now reconnect with write permissions."
#         }
#     except NoItemsFound:
#         return {
#             "success": False,
#             "message": "Trello is not connected"
#         }
#     except Exception as e:
#         return {
#             "success": False,
#             "message": f"Failed to disconnect Trello: {str(e)}"
#         }


# def get_trello_boards(api_key: str) -> Dict[str, Any]:
#     """
#     Fetch all Trello boards for the authenticated user
    
#     Args:
#         api_key: Composio API key
        
#     Returns:
#         Dictionary with boards list (id, name, url, etc.)
#     """
#     toolset = ComposioToolSet(api_key=api_key)
#     entity = toolset.get_entity()
    
#     # Check if Trello is connected first
#     try:
#         connection = entity.get_connection(app="trello")
#         if connection.status != "ACTIVE":
#             raise RuntimeError("Trello is not connected. Please connect Trello first.")
#     except NoItemsFound:
#         raise RuntimeError("Trello is not connected. Please connect Trello first.")
    
#     try:
#         # Use TRELLO_GET_MEMBERS_BOARDS_BY_ID_MEMBER action to get boards
#         result = toolset.execute_action(
#             action="TRELLO_GET_MEMBERS_BOARDS_BY_ID_MEMBER",
#             params={"id": "me"},
#             entity_id=entity.id
#         )
        
#         # Extract boards from result
#         boards = []
#         if isinstance(result, dict):
#             if "data" in result and isinstance(result["data"], list):
#                 boards = result["data"]
#             elif isinstance(result, list):
#                 boards = result
#             elif "boards" in result:
#                 boards = result["boards"]
#         elif isinstance(result, list):
#             boards = result
        
#         # Format boards for response
#         formatted_boards = []
#         for board in boards:
#             if isinstance(board, dict):
#                 formatted_boards.append({
#                     "id": board.get("id", ""),
#                     "name": board.get("name", ""),
#                     "url": board.get("url", ""),
#                     "closed": board.get("closed", False),
#                     "organization": board.get("organization", {}).get("name", "") if isinstance(board.get("organization"), dict) else ""
#                 })
        
#         return {
#             "boards": formatted_boards,
#             "count": len(formatted_boards)
#         }
#     except Exception as e:
#         # If the action doesn't work, return empty with error message
#         return {
#             "boards": [],
#             "count": 0,
#             "error": f"Failed to fetch boards: {str(e)}",
#             "note": "Please manually enter your board ID from Trello"
#         }


# def get_trello_cards(api_key: str, board_id: str) -> Dict[str, Any]:
#     """
#     Fetch all cards from a Trello board with full details
    
#     Args:
#         api_key: Composio API key
#         board_id: Trello board ID
        
#     Returns:
#         Dictionary with cards and their full details
#     """
#     toolset = ComposioToolSet(api_key=api_key)
#     entity = toolset.get_entity()
    
#     # Check if Trello is connected first
#     try:
#         connection = entity.get_connection(app="trello")
#         if connection.status != "ACTIVE":
#             raise RuntimeError("Trello is not connected. Please connect Trello first.")
#     except NoItemsFound:
#         raise RuntimeError("Trello is not connected. Please connect Trello first.")
    
#     try:
#         # Get all cards on the board
#         cards_result = toolset.execute_action(
#             action="TRELLO_GET_BOARDS_CARDS_BY_ID_BOARD",
#             params={"idBoard": board_id}
#         )
        
#         # Parse cards - handle API response structure: {successful: bool, data: object, error?: string}
#         all_cards = []
#         if isinstance(cards_result, dict):
#             if cards_result.get("successful") is False:
#                 error_msg = cards_result.get("error", "Unknown error")
#                 raise RuntimeError(f"Trello API error: {error_msg}")
            
#             data = cards_result.get("data", {})
#             if isinstance(data, list):
#                 all_cards = data
#             elif isinstance(data, dict):
#                 if "cards" in data:
#                     all_cards = data["cards"]
#                 else:
#                     # Check if any key contains a list of card-like objects
#                     for key, value in data.items():
#                         if isinstance(value, list) and len(value) > 0:
#                             if isinstance(value[0], dict) and "id" in value[0] and ("name" in value[0] or "idList" in value[0]):
#                                 all_cards = value
#                                 break
#         elif isinstance(cards_result, list):
#             all_cards = cards_result
        
#         print(f"Found {len(all_cards)} cards from Trello API for board {board_id}")
        
#         # Format cards with all available information
#         formatted_cards = []
#         for card in all_cards:
#             if not isinstance(card, dict):
#                 continue
            
#             card_id = card.get("id", "")
#             if not card_id:
#                 continue
            
#             list_id = card.get("idList", "")
            
#             # Get comments count from badges if available
#             badges = card.get("badges", {})
#             comments_count = 0
#             checklists_count = 0
#             if isinstance(badges, dict):
#                 comments_count = badges.get("comments", 0)
#                 checklists_count = badges.get("checkItems", 0)
            
#             formatted_cards.append({
#                 "id": card_id,
#                 "name": card.get("name", ""),
#                 "desc": card.get("desc", ""),
#                 "closed": card.get("closed", False),
#                 "shortUrl": card.get("shortUrl", ""),
#                 "url": card.get("url", ""),
#                 "dateLastActivity": card.get("dateLastActivity", ""),
#                 "due": card.get("due", ""),
#                 "dueComplete": card.get("dueComplete", False),
#                 "list_id": list_id,
#                 "list_name": card.get("list", {}).get("name", "") if isinstance(card.get("list"), dict) else "",
#                 "comments_count": comments_count,
#                 "badges": card.get("badges", {}),
#                 "labels": card.get("labels", []),
#                 "members": card.get("idMembers", []),
#                 "checklists_count": checklists_count
#             })
        
#         return {
#             "cards": formatted_cards,
#             "count": len(formatted_cards)
#         }
#     except Exception as e:
#         import traceback
#         error_trace = traceback.format_exc()
#         print(f"ERROR in get_trello_cards: {str(e)}")
#         print(f"Traceback: {error_trace}")
#         raise RuntimeError(f"Failed to fetch Trello cards: {str(e)}")

    


# # def delete_connection( API_KEY ,CONNECTED_ACCOUNT_ID):

# #     url = f"https://backend.composio.dev/api/v1/client/auth/project/delete/{CONNECTED_ACCOUNT_ID}"
# #     headers = {
# #         "x-api-key": API_KEY,
# #     }

# #     response = requests.delete(url, headers=headers)
# #     print(response.json())
# #     if response.status_code == 200:
# #         print("Connection deleted successfully.")
# #     else:
# #         print(f"Failed to delete connection: {response.status_code}, {response.text}")




 

# if __name__ == "__main__":
#     # prefer env var; fall back to the key you used earlier
#     api_key = os.environ.get("COMPOSIO_API_KEY", "juf2w1g7jdsu6ms5qr7l")

#     # 1) Check whether Trello is already connected
#     trello_ok = check_connection("trello", api_key)
#     print("Trello connected?", trello_ok)

#     # 2) If not connected, initiate Trello OAuth (Trello uses OAUTH1)
#     if not trello_ok:
#         print("\nTrello not connected. Initiating connection...")
#         redirect_url = create_connection_oauth2("trello", api_key, auth_scheme="OAUTH1")
#         print("Open the following URL in your browser and complete the Trello OAuth flow:")
#         print(redirect_url)
#         print("\nAfter authorizing, re-run this script to verify the connection.")


