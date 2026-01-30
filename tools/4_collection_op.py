import os
os.chdir('/home/xingao/code/cosmos-dataset-search')

# step2 list available pipelines
import requests

response = requests.get("http://localhost:8888/v1/pipelines")
pipelines = response.json()

for pipeline in pipelines.get("pipelines", []):
    print(f"Pipeline: {pipeline['id']}")
    print(f"  Enabled: {pipeline['enabled']}")
    print(f"  Description: {pipeline['config']['index']['description']}")

# step4 list collections
import requests

response = requests.get("http://localhost:8888/v1/collections")
collections = response.json()

for collection in collections.get("collections", []):
    print(f"Collection ID: {collection['id']}")
    print(f"  Name: {collection['name']}")
    print(f"  Pipeline: {collection['pipeline']}")
    print(f"  Created: {collection['created_at']}")

collection_id = collections["collections"][0]["id"]
print(f"\nUsing collection ID: {collection_id}")
