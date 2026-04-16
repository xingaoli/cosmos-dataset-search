#!/usr/bin/env python3
"""On-the-fly H.265 -> H.264 transcoding proxy.

Downloads video from S3 to /tmp (needed because MP4 moov atom is at EOF,
ffmpeg cannot seek in a pipe), transcodes to H.264, streams result back.

Usage:
    python transcode_proxy.py                    # default port 9999
    PORT=8888 python transcode_proxy.py          # custom port
    S3_ENDPOINT=http://localstack:4566 python transcode_proxy.py
"""

import boto3
import os
import subprocess
import tempfile
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# Configuration (override via environment variables)
S3_ENDPOINT = os.environ.get('S3_ENDPOINT', 'http://localstack:4566')
S3_BUCKET = os.environ.get('S3_BUCKET', 'cosmos-test-bucket')
PORT = int(os.environ.get('PORT', '9999'))

s3_client = boto3.client(
    's3',
    endpoint_url=S3_ENDPOINT,
    aws_access_key_id='test',
    aws_secret_access_key='test',
    region_name='us-east-1',
)


class TranscodeHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        parsed = urlparse(self.path)
        if parsed.path != '/transcode':
            self.send_error(404, "Use /transcode?key=<s3_key>")
            return

        params = parse_qs(parsed.query)
        key = params.get('key', [None])[0]
        if not key:
            self.send_error(400, "Missing 'key' parameter")
            return

        print(f"[transcode] start: {key}", flush=True)

        # Download from S3 to temp file (MP4 moov atom at EOF requires seek)
        tmp_in = None
        try:
            tmp_in = tempfile.NamedTemporaryFile(suffix='.mp4', delete=False)
            s3_resp = s3_client.get_object(Bucket=S3_BUCKET, Key=key)
            for chunk in s3_resp['Body'].iter_chunks(65536):
                tmp_in.write(chunk)
            tmp_in.close()
            print(f"[transcode] downloaded: {os.path.getsize(tmp_in.name)} bytes", flush=True)
        except Exception as e:
            if tmp_in:
                tmp_in.close()
            self.send_error(404, f"S3 error: {e}")
            return

        # ffmpeg: H.265 -> H.264, 720p, normal MP4 with moov at front
        tmp_out = tmp_in.name.replace('.mp4', '_out.mp4')
        cmd = [
            'ffmpeg',
            '-i', tmp_in.name,
            '-c:v', 'libx264', '-preset', 'fast', '-crf', '23',
            '-vf', 'scale=1280:720',
            '-c:a', 'aac', '-b:a', '128k',
            '-movflags', '+faststart',
            '-y', tmp_out,
        ]

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            _, stderr = proc.communicate(timeout=120)
        except FileNotFoundError:
            os.unlink(tmp_in.name)
            self.send_error(500, "ffmpeg not found in container")
            return
        except subprocess.TimeoutExpired:
            proc.kill()
            os.unlink(tmp_in.name)
            self.send_error(504, "Transcode timeout")
            return
        finally:
            os.unlink(tmp_in.name)

        if proc.returncode != 0:
            print(f"[transcode] ffmpeg exit {proc.returncode} for {key}", flush=True)
            print(f"  {stderr.decode()[-300:]}", flush=True)
            self.send_error(500, "Transcode failed")
            return

        # Read transcoded file and send as response
        out_size = os.path.getsize(tmp_out)
        print(f"[transcode] done: {key} ({out_size} bytes)", flush=True)

        self.send_response(200)
        self.send_header('Content-Type', 'video/mp4')
        self.send_header('Content-Length', str(out_size))
        self.send_header('Connection', 'close')
        self.end_headers()

        try:
            with open(tmp_out, 'rb') as f:
                while True:
                    chunk = f.read(65536)
                    if not chunk:
                        break
                    self.wfile.write(chunk)
        except BrokenPipeError:
            print(f"[transcode] client disconnected: {key}", flush=True)
        except Exception as e:
            print(f"[transcode] error: {key}: {e}", flush=True)
        finally:
            try:
                os.unlink(tmp_out)
            except OSError:
                pass

    def log_message(self, format, *args):
        pass


if __name__ == '__main__':
    server = HTTPServer(('0.0.0.0', PORT), TranscodeHandler)
    print(f"Transcode proxy listening on :{PORT}", flush=True)
    print(f"  S3: {S3_ENDPOINT}  Bucket: {S3_BUCKET}", flush=True)
    print(f"  ffmpeg: H.265 -> H.264 (720p, libx264 fast crf23)", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down.")
        server.shutdown()
