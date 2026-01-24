#!/bin/bash
set -e

# Apply database migrations
alembic upgrade head

# Start the server
export AWS_PROFILE=ModernRemodelingAWSAccount
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload