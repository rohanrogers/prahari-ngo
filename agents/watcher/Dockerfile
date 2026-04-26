FROM python:3.11-slim

WORKDIR /app

COPY shared/ /app/shared/

COPY agents/watcher/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY agents/watcher/ /app/agents/watcher/

ENV PYTHONPATH=/app

EXPOSE 8080

CMD ["uvicorn", "agents.watcher.main:app", "--host", "0.0.0.0", "--port", "8080"]
