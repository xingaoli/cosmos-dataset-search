import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
env_path = Path(__file__).parent.parent / 'deploy' / 'standalone' / '.env'
load_dotenv(env_path)

# 设置项目根目录
PROJECT_ROOT = os.getenv('PROJECT_ROOT',
                         str(Path(__file__).parent.parent))
os.chdir(PROJECT_ROOT)

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
