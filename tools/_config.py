"""Centralized configuration for all tools scripts.

Reads from deploy/standalone/.env. Override any value via environment variable.
"""

import os
import boto3
from pathlib import Path
from dotenv import load_dotenv

# Load .env
_env_path = Path(__file__).parent.parent / 'deploy' / 'standalone' / '.env'
load_dotenv(_env_path)

# ── Project ──
PROJECT_ROOT = os.getenv('PROJECT_ROOT', str(Path(__file__).parent.parent))
os.chdir(PROJECT_ROOT)

# ── S3 / LocalStack ──
AWS_ACCESS_KEY_ID = os.getenv('AWS_ACCESS_KEY_ID', 'test')
AWS_SECRET_ACCESS_KEY = os.getenv('AWS_SECRET_ACCESS_KEY', 'test')
AWS_DEFAULT_REGION = os.getenv('AWS_DEFAULT_REGION', 'us-east-1')
# Docker containers use 'localstack:4566', host scripts use 'localhost:4566'
S3_ENDPOINT_DOCKER = os.getenv('AWS_ENDPOINT_URL', 'http://localstack:4566')
S3_ENDPOINT_HOST = 'http://localhost:4566'
S3_BUCKET = os.getenv('S3_BUCKET', 'cosmos-test-bucket')
S3_PREFIX = os.getenv('S3_PREFIX', 'phaiav/h264')

# ── API ──
API_BASE = os.getenv('CDS_API_URL', 'http://localhost:8888/v1')

# ── Pipeline & Collection ──
PIPELINE_NAME = os.getenv('TOOLS_PIPELINE', 'cosmos_video_search_milvus')
COLLECTION_NAME = os.getenv('TOOLS_COLLECTION_NAME', 'PHAIAV Videos Collection')
# Set this after running 5_create_collection.py
COLLECTION_ID = os.getenv('TOOLS_COLLECTION_ID', '')

# ── Transcode Proxy ──
TRANSCODE_PROXY_DOCKER = os.getenv('TRANSCODE_PROXY_URL', 'http://transcode-proxy:9999')
TRANSCODE_PROXY_HOST = os.getenv('TRANSCODE_PROXY_HOST', 'http://localhost:9999')

# ── Local Data Paths ──
DATA_DIR = os.getenv('DATA_DIR', str(Path(PROJECT_ROOT) / 'cds-data'))
ZIP_DIR = os.getenv('TOOLS_ZIP_DIR', '')
EXTRACT_OUTPUT_DIR = os.getenv('TOOLS_EXTRACT_OUTPUT_DIR', './cds-data/phaiav_videos/h265')


def get_s3_client(use_docker_endpoint=True):
    """Create a boto3 S3 client configured for LocalStack."""
    endpoint = S3_ENDPOINT_DOCKER if use_docker_endpoint else S3_ENDPOINT_HOST
    return boto3.client(
        's3',
        endpoint_url=endpoint,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_DEFAULT_REGION,
    )
