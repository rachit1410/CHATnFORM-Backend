# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends cron gcc libpq-dev build-essential libffi-dev libssl-dev && rm -rf /var/lib/apt/lists/*

# Copy requirements and install
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt



# Copy project code
COPY . /app/

# Default command (overridden by compose)
CMD ["uvicorn", "chatnformBE.asgi:application", "--host", "0.0.0.0", "--port", "8000"]
