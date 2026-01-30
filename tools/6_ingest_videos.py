# step 6 Ingest Videos
import boto3
import requests

collection_id = "a6499a603_28e6_4dc5_b3cd_667fdd620805"  # PHAA 1000 Collection

s3_client = boto3.client(
    's3',
    endpoint_url='http://localstack:4566',
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1'
)

bucket = 'cosmos-test-bucket'
prefix = 'phaa1000/h264'  # Use transcoded H.264 videos

print(f"Listing all .mp4 files in s3://{bucket}/{prefix}/")

paginator = s3_client.get_paginator('list_objects_v2')
# video_files = ['video70.mp4', 'video700.mp4', 'video7000.mp4', 'video7001.mp4', 'video7002.mp4']
video_files = []
for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
    if 'Contents' in page:
        for obj in page['Contents']:
            key = obj['Key']
            if key.lower().endswith('.mp4'):
                # 只取文件名（不含路径）
                filename = key.split('/')[-1]
                video_files.append(key)
print(f"Found {len(video_files)} MP4 files.")

if not video_files:
    print("No MP4 files found. Exiting.")
    exit(1)

# First, test that we can generate and access presigned URLs
print("Testing presigned URL generation...")
test_key = video_files[0]
test_url = s3_client.generate_presigned_url(
    'get_object',
    Params={'Bucket': bucket, 'Key': test_key},
    ExpiresIn=3600
)
print(f"Sample presigned URL: {test_url[:80]}...")

# Verify URL is accessible
try:
    test_response = requests.head(test_url, timeout=5)
    print(f"✓ Presigned URL is accessible (status: {test_response.status_code})")
except Exception as e:
    print(f"✗ Warning: Could not access presigned URL: {e}")
    print("  Continuing anyway...")

# Generate documents with presigned URLs
# Using presigned URLs allows browser-accessible video playback
documents = []

print(f"\nGenerating presigned URLs for {len(video_files)} videos...")

for key in video_files:
    filename = key.split('/')[-1]

    # Generate presigned URL for each video
    presigned_url = s3_client.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket, 'Key': key},
        ExpiresIn=3600  # 1 hour expiration
    )

    documents.append({
        'url': presigned_url,  # Use presigned URL (browser-accessible)
        'mime_type': 'video/mp4',
        'metadata': {'filename': filename}
    })

    print(f"  ✓ {filename}")

print(f"\n{'='*60}")
print(f"Prepared {len(documents)} video(s) for ingestion")
print(f"{'='*60}")

if len(documents) > 0:
    print(f"\nFirst document preview:")
    import json
    print(json.dumps(documents[0], indent=2))
else:
    print("\n⚠️ No documents prepared. Exiting.")
    exit(1)

print(f"\n{'='*60}")
print(f"Starting video ingestion via REST API...")
print(f"{'='*60}")
BATCH_SIZE = 3  # 每批3个视频，平衡效率和内存使用
total_ingested = 0
total_batches = (len(documents) - 1) // BATCH_SIZE + 1
print(f"Total videos: {len(documents)}")
print(f"Batch size: {BATCH_SIZE}")
print(f"Total batches: {total_batches}")
for i in range(0, len(documents), BATCH_SIZE):
    batch = documents[i:i + BATCH_SIZE]
    batch_num = i // BATCH_SIZE + 1

    print(f"\n{'─'*60}")
    print(f"Batch {batch_num}/{total_batches} ({len(batch)} video(s))")
    print(f"{'─'*60}")
    print(f"Starting request...")

    import time
    start_time = time.time()

    try:
        response = requests.post(
            f"http://localhost:8888/v1/collections/{collection_id}/documents",
            json=batch,
            timeout=300  # 5 minute timeout for URL-based ingestion
        )

        elapsed_time = time.time() - start_time
        print(f"Request completed in {elapsed_time:.1f} seconds")

        if response.status_code == 200:
            result = response.json()
            ingested_count = len(result.get('documents', []))
            total_ingested += ingested_count

            # 计算处理速度
            if elapsed_time > 0:
                videos_per_min = (ingested_count / elapsed_time) * 60
                print(f"✓ Batch {batch_num} succeeded: {ingested_count} video(s)")
                print(f"  Speed: {videos_per_min:.2f} videos/minute")

            # 打印文档 ID
            if ingested_count > 0:
                doc_ids = [d['id'][:16] + '...' for d in result['documents'][:3]]
                print(f"  Document IDs: {doc_ids}")
                if ingested_count > 3:
                    print(f"  ... and {ingested_count - 3} more")
        else:
            print(f"✗ Batch {batch_num} failed with status code: {response.status_code}")
            print(f"  Response: {response.text[:500]}")  # 只显示前500字符

            # 如果是500错误，建议查看容器日志
            if response.status_code == 500:
                print("\n💡 Tip: Check container logs for detailed error:")
                print("   docker logs visual-search --tail 50")
                print("   docker logs cosmos-embed --tail 50")

            # Continue with next batch automatically
            print("\nContinuing with next batch...")

    except requests.exceptions.Timeout:
        elapsed_time = time.time() - start_time
        print(f"✗ Batch {batch_num} timed out after {elapsed_time:.1f} seconds")
        print("\n💡 Suggestions:")
        print("   1. Check cosmos-embed service: docker logs cosmos-embed --tail 50")
        print("   2. Check GPU usage: nvidia-smi")
        print("   3. Check network connectivity to LocalStack")
        print("   4. Try reducing BATCH_SIZE in api_guide.py")
        continue
    except Exception as e:
        elapsed_time = time.time() - start_time
        print(f"⚠️  Batch {batch_num} raised exception after {elapsed_time:.1f}s: {type(e).__name__}")
        print(f"  Error: {e}")
        import traceback
        print("\nFull traceback:")
        traceback.print_exc()
        continue

print(f"\n{'='*60}")
print(f"Ingestion Summary")
print(f"{'='*60}")
print(f"Total videos prepared: {len(documents)}")
print(f"Total videos ingested: {total_ingested}")
print(f"Success rate: {total_ingested}/{len(documents)} ({100*total_ingested/len(documents) if len(documents) > 0 else 0:.1f}%)")

if total_ingested == len(documents):
    print(f"\n✅ All videos successfully ingested!")
else:
    print(f"\n⚠️  Some videos failed to ingest.")
    print(f"💡 Check the container logs for details:")
    print(f"   docker logs visual-search --tail 100")
    print(f"   docker logs cosmos-embed --tail 100")
