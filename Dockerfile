FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system app \
    && useradd --system --gid app --create-home --home-dir /home/app app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONPATH=/app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
# Ch.19 — disable debug by default
ENV DEBUG=0

RUN mkdir -p /app/data /app/data/logs \
    && chown -R app:app /app/data

USER app

EXPOSE 8000

CMD ["python", "-m", "src.main", "serve"]
