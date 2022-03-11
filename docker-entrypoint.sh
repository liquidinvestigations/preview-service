#!/usr/bin/env bash

set -ex

Xvfb :99 -screen 0 1x1x16 > /dev/null 2>&1 &

mkdir -p /tmp/files
mkdir -p /tmp/cache

# DISPLAY=:99.0 uvicorn --host 0.0.0.0 --port 8000 app:app
# must use sync for timeout to work:
# https://github.com/benoitc/gunicorn/issues/2695
DISPLAY=:99.0 gunicorn -b 0.0.0.0:8000 \
  --timeout=200 \
  --worker-class=sync --workers 30 \
  --max-requests 30 --max-requests-jitter 20 \
  app:app
