# step8: delete collection
import requests

collection_id = "ceb00b99_39c0_409c_a7cf_8019cf8b9f29"

response = requests.delete(
    f"http://localhost:8888/v1/collections/{collection_id}"
)

print(f"Collection deleted: {response.status_code}")
