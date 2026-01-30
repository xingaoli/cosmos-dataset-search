# step 7： search video
import requests
import json
import subprocess

collection_id = "a4babf42c_c97c_4a5c_84f8_2ed44e2401db"  # URL Format Collection

# Get presigned URL for the video
# IMPORTANT: Use localstack hostname instead of localhost so cosmos-embed container can access it
s3_path = "s3://cosmos-test-bucket/phaa_videos100/h264/c3ca785e-3876-4a0a-a8bd-890f2027d795.camera_front_wide_120fov.mp4"
result = subprocess.run(
    ["aws", "s3", "presign", s3_path, "--expires-in", "3600"],
    capture_output=True,
    text=True,
    env={**subprocess.os.environ, "AWS_ACCESS_KEY_ID": "test", "AWS_SECRET_ACCESS_KEY": "test", "AWS_ENDPOINT_URL": "http://localstack:4566"}
)
presigned_url = result.stdout.strip()
print(presigned_url)

search_payload = {
    "query": [{"video": presigned_url}],
    "top_k": 5
}

print(f"Searching collection: {collection_id}")
print(f"Query video: {presigned_url}\n")

response = requests.post(
    f"http://localhost:8888/v1/collections/{collection_id}/search",
    json=search_payload
)

print(f"Response status: {response.status_code}")

if response.status_code != 200:
    print(f"Error: {response.text}")
else:
    results = response.json()
    
    retrievals = results.get('retrievals', [])
    print(f"Found {len(retrievals)} results:\n")
    
    for i, result in enumerate(retrievals, 1):
        print(f"Result {i}:")
        print(f"  Score: {result['score']:.4f}")
        if 'metadata' in result:
            if 'filename' in result['metadata']:
                print(f"  Filename: {result['metadata']['filename']}")
            if 'source_url' in result['metadata']:
                print(f"  Video: {result['metadata']['source_url']}...")