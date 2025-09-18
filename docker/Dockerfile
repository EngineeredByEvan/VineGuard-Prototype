FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY edge ./edge
COPY simulate_node.py ./simulate_node.py

CMD ["python", "-m", "edge.gateway"]
