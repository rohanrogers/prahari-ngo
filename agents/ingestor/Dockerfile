FROM python:3.11-slim

WORKDIR /app

# Copy shared libraries first (for layer caching)
COPY shared/ /app/shared/

# Copy agent code
COPY agents/ingestor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/ingestor/ /app/agents/ingestor/

# Set Python path for shared imports
ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["uvicorn", "agents.ingestor.main:app", "--host", "0.0.0.0", "--port", "8080"]
