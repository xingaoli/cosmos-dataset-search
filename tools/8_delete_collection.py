"""Delete a collection."""
import requests
from _config import COLLECTION_ID, API_BASE

if not COLLECTION_ID:
    print("ERROR: Set TOOLS_COLLECTION_ID in deploy/standalone/.env")
    exit(1)

response = requests.delete(f"{API_BASE}/collections/{COLLECTION_ID}")
print(f"Collection {COLLECTION_ID} deleted: {response.status_code}")
