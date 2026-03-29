FROM python:3.13.7-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY pyproject.toml ./
COPY app ./app
COPY alembic.ini ./
COPY alembic ./alembic/

RUN pip install --no-cache-dir -e .

RUN mkdir -p /uploads

ENV UPLOAD_DIR=/uploads
EXPOSE 8000
