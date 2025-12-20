
from composio import ComposioToolSet, App
from composio.client.exceptions import NoItemsFound
import os

import requests

# os.environ["COMPOSIO_API_KEY"] =  os.getenv("COMPOSIO_API_KEY")

def create_connection_oauth2(app_name,api_key, auth_scheme="OAUTH2"):
    toolset = ComposioToolSet(api_key=api_key)
    connection_request = toolset.initiate_connection(
        app=app_name, # user comes here after oauth flow
        # entity_id=entity_id,
        auth_scheme=auth_scheme,
    )
    print(connection_request.connectedAccountId,connection_request.connectionStatus)
    # Redirect user to the redirect url so they complete the oauth flow
    print(connection_request.redirectUrl)
    return connection_request.redirectUrl


def check_connection( app_name, api_key):
    toolset = ComposioToolSet(api_key=api_key)

    # Filter based on entity id
    entity = toolset.get_entity()  # fill entity id here

    try:
        # Filters based on app name
        connection_details = entity.get_connection(app=app_name) 

        print(connection_details)
        if connection_details.status == "ACTIVE":
            return True
        else:
            return False

    except NoItemsFound as e:
        print("No connected account found")
        return False
    
# def delete_connection( API_KEY ,CONNECTED_ACCOUNT_ID):

#     url = f"https://backend.composio.dev/api/v1/client/auth/project/delete/{CONNECTED_ACCOUNT_ID}"
#     headers = {
#         "x-api-key": API_KEY,
#     }

#     response = requests.delete(url, headers=headers)
#     print(response.json())
#     if response.status_code == 200:
#         print("Connection deleted successfully.")
#     else:
#         print(f"Failed to delete connection: {response.status_code}, {response.text}")


 

if __name__ == "__main__":
    # prefer env var; fall back to the key you used earlier
    api_key = os.environ.get("COMPOSIO_API_KEY", "fyvn2yln306o052h5mt007")

    # 1) Check whether Trello is already connected
    trello_ok = check_connection("trello", api_key)
    print("Trello connected?", trello_ok)

    # 2) If not connected, initiate Trello OAuth (Trello uses OAUTH1)
    if not trello_ok:
        print("\nTrello not connected. Initiating connection...")
        redirect_url = create_connection_oauth2("trello", api_key, auth_scheme="OAUTH1")
        print("Open the following URL in your browser and complete the Trello OAuth flow:")
        print(redirect_url)
        print("\nAfter authorizing, re-run this script to verify the connection.")


