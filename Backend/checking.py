from composio_langchain import ComposioToolSet


toolset = ComposioToolSet(api_key=composio_api_key)
entity = toolset.get_entity()

try:
    conn = entity.get_connection(app="trello")
    print("Trello connected:", conn.status, conn.id)
except Exception as e:
    print("❌ Trello NOT connected:", e)
