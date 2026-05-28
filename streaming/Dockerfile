FROM python:3.11-slim

WORKDIR /app

COPY streaming/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY streaming/consumer/ ./consumer/
COPY config.py .

ENV PYTHONPATH=/app

CMD ["python", "-u", "consumer/ratings_consumer.py"]
