#!/bin/bash
set -e
python init_langfuse.py
if [ -f /tmp/langfuse.env ]; then
  . /tmp/langfuse.env
fi
exec uvicorn main:app --host 0.0.0.0 --port 8000
