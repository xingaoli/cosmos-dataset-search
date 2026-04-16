"""List pipelines and collections."""
import requests
from _config import API_BASE

# List pipelines
response = requests.get(f"{API_BASE}/pipelines")
pipelines = response.json()

for pipeline in pipelines.get("pipelines", []):
    print(f"Pipeline: {pipeline['id']}")
    print(f"  Enabled: {pipeline['enabled']}")
    print(f"  Description: {pipeline['config']['index']['description']}")

# List collections
response = requests.get(f"{API_BASE}/collections")
collections = response.json()

print()
for collection in collections.get("collections", []):
    print(f"Collection ID: {collection['id']}")
    print(f"  Name: {collection['name']}")
    print(f"  Pipeline: {collection['pipeline']}")
    print(f"  Created: {collection['created_at']}")

if collections.get("collections"):
    collection_id = collections["collections"][0]["id"]
    print(f"\nUsing collection ID: {collection_id}")
    print(f"  -> Set TOOLS_COLLECTION_ID={collection_id} in deploy/standalone/.env")
