FROM python:3.12-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8080

# Set the working directory
WORKDIR /app

# Install system-level dependencies. postgresql-client is pulled from PGDG
# rather than Debian, because Debian bookworm ships pg_dump 15 and pg_dump
# refuses to dump a server newer than itself (Supabase runs Postgres 17).
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    ca-certificates \
    && install -d /usr/share/postgresql-common/pgdg \
    && curl --fail -o /usr/share/postgresql-common/pgdg/apt.postgresql.org.asc \
        https://www.postgresql.org/media/keys/ACCC4CF8.asc \
    && echo "deb [signed-by=/usr/share/postgresql-common/pgdg/apt.postgresql.org.asc] https://apt.postgresql.org/pub/repos/apt bookworm-pgdg main" \
        > /etc/apt/sources.list.d/pgdg.list \
    && apt-get update && apt-get install -y --no-install-recommends postgresql-client-17 \
    && rm -rf /var/lib/apt/lists/*

# Copy the project files into the container
COPY . /app

# Install Python dependencies
RUN pip install --upgrade pip
RUN pip install -e .

# Expose the application port
EXPOSE 8080

# Run the application with gunicorn. Cloud Run injects $PORT, so bind to it
# rather than a fixed port. Frontend JS deps are vendored in
# src/static/js/vendors, so no Node.js toolchain is needed at build or runtime.
CMD exec gunicorn \
    --workers=2 \
    --threads=3 \
    --timeout 30 \
    --max-requests=300 \
    --max-requests-jitter=100 \
    --graceful-timeout=15 \
    --preload \
    --worker-tmp-dir=/dev/shm \
    --bind 0.0.0.0:$PORT \
    src.app:app
