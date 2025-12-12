# =========================================
# Stage 1: Build environment
# =========================================
FROM python:3.12-slim AS builder

WORKDIR /app

COPY requirements.txt .
# Install Python dependencies early for caching
# RUN apt-get update && apt-get install -y build-essential libpq-dev && rm -rf /var/lib/apt/lists/*
RUN pip install --upgrade pip && pip install -r requirements.txt
# ENV variable
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=on

COPY . .
WORKDIR /app/core
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
