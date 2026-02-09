#!/bin/bash
set -e

echo "Starting application..."

# Wait for database to be ready
echo "Waiting for database connection..."
python << END
import time
import sys
from sqlalchemy import create_engine
from app.core.config import settings

max_retries = 30
retry_interval = 2

for i in range(max_retries):
    try:
        engine = create_engine(settings.database_url)
        connection = engine.connect()
        connection.close()
        print("Database is ready!")
        sys.exit(0)
    except Exception as e:
        if i < max_retries - 1:
            print(f"Database not ready yet, retrying in {retry_interval}s... ({i+1}/{max_retries})")
            time.sleep(retry_interval)
        else:
            print(f"Failed to connect to database after {max_retries} attempts")
            sys.exit(1)
END

# Apply database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the server
echo "Starting FastAPI server..."
if [ "$APP_ENV" = "production" ]; then
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 2
else
    exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --reload
fi