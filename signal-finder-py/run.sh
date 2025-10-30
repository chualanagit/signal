#!/usr/bin/env bash
export PYTHONUNBUFFERED=1
# Load environment variables from .env file
set -a
source .env
set +a
uvicorn main:app --reload --port 8000
