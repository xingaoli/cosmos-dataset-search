"""Create a collection and print its ID (copy to .env TOOLS_COLLECTION_ID)."""
import requests
from _config import API_BASE, PIPELINE_NAME, COLLECTION_NAME, S3_BUCKET, S3_PREFIX

payload = {
    "pipeline": PIPELINE_NAME,
    "name": COLLECTION_NAME,
    "tags": {
        "storage-template": f"s3://{S3_BUCKET}/{S3_PREFIX}/{{filename}}"
    }
}

response = requests.post(f"{API_BASE}/collections", json=payload)

if response.status_code != 200:
    print(f"Error {response.status_code}: {response.text}")
    exit(1)

collection = response.json()
collection_id = collection['collection']['id']
print(f"Created collection: {collection_id}")
print(f"  Name: {COLLECTION_NAME}")
print(f"\n  -> Set TOOLS_COLLECTION_ID={collection_id} in deploy/standalone/.env")
