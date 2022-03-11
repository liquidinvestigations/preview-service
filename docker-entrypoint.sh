#!/usr/bin/env bash

set -ex

Xvfb :99 -screen 0 1x1x16 > /dev/null 2>&1 &

mkdir -p /tmp/files
mkdir -p /tmp/cache

# DISPLAY=:99.0 uvicorn --host 0.0.0.0 --port 8000 app:app
# must use sync for timeout to work:
# https://github.com/benoitc/gunicorn/issues/2695
DISPLAY=:99.0 gunicorn -b 0.0.0.0:8000 \
  --name thumbnail-preview-service \
  --worker-class uvicorn.workers.UvicornWorker --threads 1 \
  --workers 4 \
  --timeout=200 \
  --max-requests 50 --max-requests-jitter 30 \
  app:app
