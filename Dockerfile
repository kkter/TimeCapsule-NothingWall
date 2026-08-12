FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DATA_DIR=/app/data \
    WEB_PORT=9000

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY time_capsule.py index.html favicon.ico favicon-32x32.png apple-touch-icon.png robots.txt sitemap.xml ./
RUN mkdir -p /app/data

EXPOSE 9000

CMD ["python", "time_capsule.py"]
