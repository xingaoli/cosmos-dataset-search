import os
os.chdir('/home/xingao/code/cosmos-dataset-search')

# # step2 list available pipelines
# import requests

# response = requests.get("http://localhost:8888/v1/pipelines")
# pipelines = response.json()

# for pipeline in pipelines.get("pipelines", []):
#     print(f"Pipeline: {pipeline['id']}")
#     print(f"  Enabled: {pipeline['enabled']}")
#     print(f"  Description: {pipeline['config']['index']['description']}")


# # step3 create a collection
# import requests

# payload = {
#     "pipeline": "cosmos_video_search_milvus",
#     "name": "My First Video Collection",
#     "tags": {
#         "storage-template": "s3://cosmos-test-bucket/videos/{{filename}}"
#     }
# }

# response = requests.post(
#     "http://localhost:8888/v1/collections",
#     json=payload
# )

# collection = response.json()
# collection_id = collection['collection']['id']
# print(f"Created collection: {collection_id}") # a86af2c3_02ea_42cf_9af5_efabbe342144


# # step4 list collections
# import requests

# response = requests.get("http://localhost:8888/v1/collections")
# collections = response.json()

# for collection in collections.get("collections", []):
#     print(f"Collection ID: {collection['id']}")
#     print(f"  Name: {collection['name']}")
#     print(f"  Pipeline: {collection['pipeline']}")
#     print(f"  Created: {collection['created_at']}")

# collection_id = collections["collections"][0]["id"]
# print(f"\nUsing collection ID: {collection_id}")

# # step5 Upload Videos to LocalStack
# import boto3
# from pathlib import Path

# s3_client = boto3.client(
#     's3',
#     endpoint_url='http://localhost:4566',
#     aws_access_key_id='test',
#     aws_secret_access_key='test',
#     region_name='us-east-1'
# )

# bucket = 'cosmos-test-bucket'
# prefix = 'videos'

# video_files = list(Path('./cds-data/physical_ai_av_videos').glob('*.mp4'))

# print(f"Uploading {len(video_files)} videos to s3://{bucket}/{prefix}/")

# for video_file in video_files:
#     key = f"{prefix}/{video_file.name}"
#     print(f"  Uploading {video_file.name}...")
#     s3_client.upload_file(str(video_file), bucket, key)

# print("\nUpload complete! Verifying...")

# response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix)
# if 'Contents' in response:
#     print(f"\nFiles in s3://{bucket}/{prefix}/:")
#     for obj in response['Contents']:
#         size_mb = obj['Size'] / (1024 * 1024)
#         print(f"  {obj['Key']} ({size_mb:.2f} MB)")
# else:
#     print("No files found in bucket")


# # step 6 Ingest Videos
# import boto3
# import requests

# collection_id = "a86af2c3_02ea_42cf_9af5_efabbe342144"  # Replace with your actual collection ID

# s3_client = boto3.client(
#     's3',
#     endpoint_url='http://localstack:4566',
#     aws_access_key_id='test',
#     aws_secret_access_key='test',
#     region_name='us-east-1'
# )

# bucket = 'cosmos-test-bucket'
# prefix = 'videos'

# print(f"Listing all .mp4 files in s3://{bucket}/{prefix}/")

# paginator = s3_client.get_paginator('list_objects_v2')
# # video_files = ['video70.mp4', 'video700.mp4', 'video7000.mp4', 'video7001.mp4', 'video7002.mp4']
# video_files = []
# for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
#     if 'Contents' in page:
#         for obj in page['Contents']:
#             key = obj['Key']
#             if key.lower().endswith('.mp4'):
#                 # 只取文件名（不含路径）
#                 filename = key.split('/')[-1]
#                 video_files.append(key)
# print(f"Found {len(video_files)} MP4 files.")

# if not video_files:
#     print("No MP4 files found. Exiting.")
#     exit(1)

# # First, test that we can generate and access presigned URLs
# print("Testing presigned URL generation...")
# test_key = video_files[0]
# test_url = s3_client.generate_presigned_url(
#     'get_object',
#     Params={'Bucket': bucket, 'Key': test_key},
#     ExpiresIn=3600
# )
# print(f"Sample presigned URL: {test_url[:80]}...")

# # Verify URL is accessible
# try:
#     test_response = requests.head(test_url, timeout=5)
#     print(f"✓ Presigned URL is accessible (status: {test_response.status_code})")
# except Exception as e:
#     print(f"✗ Warning: Could not access presigned URL: {e}")
#     print("  Continuing anyway...")

# # Generate documents with base64-encoded video content
# # Note: Using base64 instead of presigned URLs to avoid timeout issues
# # Videos will be automatically transcoded to H.264 codec (cosmos-embed requirement)
# import base64
# import subprocess
# import tempfile
# import os

# def transcode_to_h264(video_data: bytes, filename: str) -> bytes:
#     """Transcode video to H.264 codec using ffmpeg.

#     Cosmos-embed only supports H.264 encoded videos. This function transcodes
#     HEVC/H.265 and other codecs to H.264 with reasonable quality settings.
#     """
#     print(f"  Transcoding {filename} to H.264...")

#     # Save original video to temp file
#     with tempfile.NamedTemporaryFile(suffix='_original.mp4', delete=False) as f:
#         temp_input = f.name
#         f.write(video_data)

#     temp_output = temp_input.replace('_original.mp4', '_h264.mp4')

#     try:
#         # Transcode using ffmpeg
#         # -c:v libx264: H.264 codec
#         # -preset fast: Balance between speed and compression
#         # -crf 23: Quality (18-28 is reasonable, lower = better quality)
#         # -vf scale=1280:720: Downscale to 720p for faster processing
#         # -c:a aac: Audio codec
#         subprocess.run([
#             'ffmpeg', '-i', temp_input,
#             '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
#             '-vf', 'scale=1280:720',
#             '-c:a', 'aac', '-b:a', '128k',
#             '-y', temp_output
#         ], capture_output=True, check=True)

#         # Read transcoded video
#         with open(temp_output, 'rb') as f:
#             transcoded_data = f.read()

#         original_size = len(video_data) / 1024 / 1024
#         transcoded_size = len(transcoded_data) / 1024 / 1024
#         print(f"  ✓ Transcoded: {original_size:.2f} MB → {transcoded_size:.2f} MB")

#         return transcoded_data

#     except subprocess.CalledProcessError as e:
#         print(f"  ✗ Transcoding failed: {e}")
#         print(f"    stderr: {e.stderr.decode('utf-8', errors='ignore')[-500:]}")
#         raise
#     finally:
#         # Cleanup temp files
#         if os.path.exists(temp_input):
#             os.unlink(temp_input)
#         if os.path.exists(temp_output):
#             os.unlink(temp_output)


# documents = []
# # 处理所有视频 - 自动转码为H.264并ingest
# test_videos = video_files  # 处理所有找到的视频

# for key in test_videos:
#     filename = key.split('/')[-1]

#     print(f"Downloading {filename} from S3...")
#     try:
#         # 从S3下载视频内容
#         response = s3_client.get_object(Bucket=bucket, Key=key)
#         original_data = response['Body'].read()
#         original_size_mb = len(original_data) / 1024 / 1024

#         print(f"  Downloaded: {filename} ({original_size_mb:.2f} MB)")

#         # Transcode to H.264 (cosmos-embed requirement)
#         video_data = transcode_to_h264(original_data, filename)

#         # Encode transcoded video to base64
#         print(f"  Encoding to base64...")
#         video_b64 = base64.b64encode(video_data).decode('utf-8')

#         documents.append({
#             'content': video_b64,  # 使用base64编码的视频内容
#             'mime_type': 'video/mp4',
#             'metadata': {
#                 'filename': filename,
#                 'transcoded': 'true',  # Mark as transcoded
#                 'original_size_mb': f"{original_size_mb:.2f}"
#             }
#         })

#         print(f"✓ Prepared {filename}")
#     except Exception as e:
#         print(f"✗ Failed to process {filename}: {e}")
#         import traceback
#         traceback.print_exc()
#         continue

# print(f"\n{'='*60}")
# print(f"Prepared {len(documents)} video(s) for ingestion")
# print(f"{'='*60}")

# if len(documents) > 0:
#     print(f"\nFirst document preview:")
#     import json
#     preview = {
#         'content': f"<base64 data, length={len(documents[0]['content'])} chars>",
#         'mime_type': documents[0]['mime_type'],
#         'metadata': documents[0]['metadata']
#     }
#     print(json.dumps(preview, indent=2))
# else:
#     print("\n⚠️ No documents prepared. Exiting.")
#     exit(1)

# print(f"\n{'='*60}")
# print(f"Starting video ingestion via REST API...")
# print(f"{'='*60}")
# BATCH_SIZE = 3  # 每批3个视频，平衡效率和内存使用
# total_ingested = 0
# total_batches = (len(documents) - 1) // BATCH_SIZE + 1
# print(f"Total videos: {len(documents)}")
# print(f"Batch size: {BATCH_SIZE}")
# print(f"Total batches: {total_batches}")
# for i in range(0, len(documents), BATCH_SIZE):
#     batch = documents[i:i + BATCH_SIZE]
#     batch_num = i // BATCH_SIZE + 1

#     print(f"\n{'─'*60}")
#     print(f"Batch {batch_num}/{total_batches} ({len(batch)} video(s))")
#     print(f"{'─'*60}")
#     print(f"Starting request...")

#     import time
#     start_time = time.time()

#     try:
#         response = requests.post(
#             f"http://localhost:8888/v1/collections/{collection_id}/documents",
#             json=batch,
#             timeout=600  # 增加到600秒（10分钟）以应对base64编码
#         )

#         elapsed_time = time.time() - start_time
#         print(f"Request completed in {elapsed_time:.1f} seconds")

#         if response.status_code == 200:
#             result = response.json()
#             ingested_count = len(result.get('documents', []))
#             total_ingested += ingested_count

#             # 计算处理速度
#             if elapsed_time > 0:
#                 videos_per_min = (ingested_count / elapsed_time) * 60
#                 print(f"✓ Batch {batch_num} succeeded: {ingested_count} video(s)")
#                 print(f"  Speed: {videos_per_min:.2f} videos/minute")

#             # 打印文档 ID
#             if ingested_count > 0:
#                 doc_ids = [d['id'][:16] + '...' for d in result['documents'][:3]]
#                 print(f"  Document IDs: {doc_ids}")
#                 if ingested_count > 3:
#                     print(f"  ... and {ingested_count - 3} more")
#         else:
#             print(f"✗ Batch {batch_num} failed with status code: {response.status_code}")
#             print(f"  Response: {response.text[:500]}")  # 只显示前500字符

#             # 如果是500错误，建议查看容器日志
#             if response.status_code == 500:
#                 print("\n💡 Tip: Check container logs for detailed error:")
#                 print("   docker logs visual-search --tail 50")
#                 print("   docker logs cosmos-embed --tail 50")

#             # 继续处理还是中止？对于base64模式，如果失败继续可能有意义
#             user_input = input("\nContinue with next batch? (y/n): ").strip().lower()
#             if user_input != 'y':
#                 print("Stopping ingestion process.")
#                 break

#     except requests.exceptions.Timeout:
#         elapsed_time = time.time() - start_time
#         print(f"✗ Batch {batch_num} timed out after {elapsed_time:.1f} seconds")
#         print("\n💡 Suggestions:")
#         print("   1. Check cosmos-embed service: docker logs cosmos-embed --tail 50")
#         print("   2. Check GPU usage: nvidia-smi")
#         print("   3. Try reducing BATCH_SIZE in api_guide.py")
#         print("   4. Try smaller test videos")
#         continue
#     except Exception as e:
#         elapsed_time = time.time() - start_time
#         print(f"⚠️  Batch {batch_num} raised exception after {elapsed_time:.1f}s: {type(e).__name__}")
#         print(f"  Error: {e}")
#         import traceback
#         print("\nFull traceback:")
#         traceback.print_exc()
#         continue

# print(f"\n{'='*60}")
# print(f"Ingestion Summary")
# print(f"{'='*60}")
# print(f"Total videos prepared: {len(documents)}")
# print(f"Total videos ingested: {total_ingested}")
# print(f"Success rate: {total_ingested}/{len(documents)} ({100*total_ingested/len(documents) if len(documents) > 0 else 0:.1f}%)")

# if total_ingested == len(documents):
#     print(f"\n✅ All videos successfully ingested!")
# else:
#     print(f"\n⚠️  Some videos failed to ingest.")
#     print(f"💡 Check the container logs for details:")
#     print(f"   docker logs visual-search --tail 100")
#     print(f"   docker logs cosmos-embed --tail 100")

# step 7： search video
