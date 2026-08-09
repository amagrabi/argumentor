"""Dump the Postgres database to GCS.

Run as a Cloud Run Job on a schedule. Supabase's free tier takes no backups of
its own, so this is the only copy of the data outside the live database.

Uses the same SQLALCHEMY_DATABASE_URI secret as the web service, and writes to
GCS via Application Default Credentials (the job's attached service account).

    python scripts/backup_db.py

Environment:
    SQLALCHEMY_DATABASE_URI  Postgres connection string (required)
    BACKUP_BUCKET            GCS bucket to write to (required)
    BACKUP_RETENTION_DAYS    Delete dumps older than this (default 30)
"""

import logging
import os
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from urllib.parse import unquote, urlparse

from google.cloud import storage

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

PREFIX = "backups/argumentor-"


def libpq_env() -> dict[str, str]:
    """Translate the SQLAlchemy URL into libpq environment variables.

    Passing the password via the environment rather than argv keeps it out of
    the process list.
    """
    parsed = urlparse(os.environ["SQLALCHEMY_DATABASE_URI"])
    env = {
        **os.environ,
        "PGHOST": parsed.hostname or "",
        "PGPORT": str(parsed.port or 5432),
        "PGDATABASE": parsed.path.lstrip("/") or "postgres",
        "PGCONNECT_TIMEOUT": "30",
        # Supabase's pooler terminates TLS; require it rather than falling back.
        "PGSSLMODE": os.environ.get("PGSSLMODE", "require"),
    }
    if parsed.username:
        env["PGUSER"] = unquote(parsed.username)
    if parsed.password:
        env["PGPASSWORD"] = unquote(parsed.password)
    return env


def prune(bucket, retention_days: int) -> None:
    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
    for blob in bucket.list_blobs(prefix=PREFIX):
        if blob.time_created < cutoff:
            logger.info("Deleting expired backup %s", blob.name)
            blob.delete()


def main() -> int:
    bucket_name = os.environ["BACKUP_BUCKET"]
    retention_days = int(os.environ.get("BACKUP_RETENTION_DAYS", "30"))
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    name = f"{PREFIX}{stamp}.dump"

    bucket = storage.Client().bucket(bucket_name)

    with tempfile.NamedTemporaryFile(suffix=".dump") as tmp:
        logger.info("Running pg_dump")
        result = subprocess.run(
            ["pg_dump", "--format=custom", "--no-owner", "--no-acl", "--file", tmp.name],
            env=libpq_env(),
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            logger.error("pg_dump failed: %s", result.stderr.strip())
            return 1

        size = os.path.getsize(tmp.name)
        if size == 0:
            logger.error("pg_dump produced an empty file; refusing to upload")
            return 1

        logger.info("Uploading %s (%d bytes) to gs://%s", name, size, bucket_name)
        bucket.blob(name).upload_from_filename(tmp.name)

    prune(bucket, retention_days)
    logger.info("Backup complete: gs://%s/%s", bucket_name, name)
    return 0


if __name__ == "__main__":
    sys.exit(main())
