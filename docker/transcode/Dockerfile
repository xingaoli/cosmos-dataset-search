FROM python:3.11-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends ffmpeg && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir boto3

COPY transcode_proxy.py /app/

WORKDIR /app

EXPOSE 9999

CMD ["python", "/app/transcode_proxy.py"]
