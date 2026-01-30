# step3 create a collection
import requests

payload = {
    "pipeline": "cosmos_video_search_milvus",
    "name": "PHAA 1000 Videos Collection",
    "tags": {
        "storage-template": "s3://cosmos-test-bucket/phaa1000/h264/{{filename}}"
    }
}

response = requests.post(
    "http://localhost:8888/v1/collections",
    json=payload
)

collection = response.json()
collection_id = collection['collection']['id']
print(f"Created collection: {collection_id}")