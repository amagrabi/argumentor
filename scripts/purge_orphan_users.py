"""One-time cleanup of anonymous user rows that were never used for anything.

Until Aug 2026 the app inserted a `users` row for every visitor arriving without
a session cookie, on every non-static request. Bots never return a cookie, so
that was one row per bot request: 253,915 rows of which 253,841 (99.97%) had no
answers, 86 MB against a 500 MB Supabase cap.

`ensure_user_id` no longer writes anything (see `src/services/user_service.py`),
so this is a backlog cleanup, not something to schedule. New orphans can still
appear — a checkout that is abandoned, feedback from someone who never submits an
answer — but at a few rows a month rather than thousands a day.

Dry run, the default, reports what it would delete and changes nothing:

    python scripts/purge_orphan_users.py

Then, with a fresh backup in hand:

    python scripts/purge_orphan_users.py --apply

Deleting rows does not shrink the database on disk. Postgres marks the space
reusable; recovering the 86 MB needs a VACUUM FULL afterwards. See the runbook in
DEPLOY.md, which also covers the disk headroom that needs.
"""

import argparse
import os
import sys
from datetime import UTC, datetime, timedelta

import psycopg2

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)), "src"))
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from config import get_settings  # noqa: E402

SETTINGS = get_settings()

# A user is safe to delete when nothing points at them and they never became a
# real account. The two NOT EXISTS clauses are the important ones:
#
# - answer: the whole point of the purge is to keep users who did something.
# - feedback: feedback.user_uuid is ON DELETE CASCADE, so deleting the user would
#   silently take their feedback message with it.
#
# visit also cascades, which is intended — those are the bot visits belonging to
# the bot users. user_achievements has no ON DELETE CASCADE at all, so it has to
# be cleared explicitly before the users delete; see delete_batch().
ORPHAN_PREDICATE = """
    FROM users u
    WHERE u.tier = 'anonymous'
      AND u.email IS NULL
      AND u.google_id IS NULL
      AND u.password_hash IS NULL
      AND u.stripe_customer_id IS NULL
      AND u.stripe_subscription_id IS NULL
      AND NOT EXISTS (SELECT 1 FROM answer a WHERE a.user_uuid = u.uuid)
      AND NOT EXISTS (SELECT 1 FROM feedback f WHERE f.user_uuid = u.uuid)
"""


def connect():
    # SQLAlchemy's "postgresql+psycopg2://" is not a libpq URL.
    dsn = SETTINGS.SQLALCHEMY_DATABASE_URI.replace("+psycopg2", "")
    return psycopg2.connect(dsn)


def report_sizes(cur, label):
    cur.execute(
        """
        SELECT pg_size_pretty(pg_total_relation_size('users')),
               pg_size_pretty(pg_total_relation_size('visit')),
               pg_size_pretty(pg_database_size(current_database()))
        """
    )
    users, visit, database = cur.fetchone()
    print(f"{label}: users {users}, visit {visit}, database {database}")


def count_orphans(cur):
    cur.execute(f"SELECT count(*) {ORPHAN_PREDICATE}")
    return cur.fetchone()[0]


def select_batch(cur, batch_size):
    cur.execute(f"SELECT u.uuid {ORPHAN_PREDICATE} LIMIT %s", (batch_size,))
    return [row[0] for row in cur.fetchall()]


def delete_batch(cur, uuids):
    # user_achievements first: its foreign key was created without ON DELETE
    # CASCADE, so the users delete would otherwise fail on any user that managed
    # to earn an achievement without keeping an answer.
    cur.execute("DELETE FROM user_achievements WHERE user_uuid = ANY(%s)", (uuids,))
    cur.execute("DELETE FROM users WHERE uuid = ANY(%s)", (uuids,))
    return cur.rowcount


def purge_users(conn, batch_size, apply):
    with conn.cursor() as cur:
        report_sizes(cur, "before")
        total = count_orphans(cur)
        cur.execute("SELECT count(*) FROM users")
        all_users = cur.fetchone()[0]

    share = (total / all_users * 100) if all_users else 0
    print(f"{total} of {all_users} users are unused orphans ({share:.2f}%)")

    if not apply:
        print("dry run, nothing deleted; pass --apply to delete")
        return 0

    if total == 0:
        return 0

    deleted = 0
    while True:
        with conn.cursor() as cur:
            uuids = select_batch(cur, batch_size)
            if not uuids:
                break
            deleted += delete_batch(cur, uuids)
        # Commit per batch, so an interrupted run is resumable and no single
        # transaction holds a quarter of a million row locks.
        conn.commit()
        print(f"deleted {deleted}/{total} users")

    return deleted


def purge_visits(conn, retention_days, batch_size, apply):
    # Naive UTC: visit.created_at is `timestamp without time zone` holding UTC
    # wall time.
    cutoff = (datetime.now(UTC) - timedelta(days=retention_days)).replace(tzinfo=None)

    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM visit WHERE created_at < %s", (cutoff,))
        total = cur.fetchone()[0]

    print(f"{total} visits are older than {cutoff.date()} ({retention_days} days)")

    if not apply or total == 0:
        return 0

    deleted = 0
    while True:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM visit
                WHERE id = ANY(
                    SELECT id FROM visit WHERE created_at < %s LIMIT %s
                )
                """,
                (cutoff, batch_size),
            )
            if cur.rowcount == 0:
                break
            deleted += cur.rowcount
        conn.commit()
        print(f"deleted {deleted}/{total} visits")

    return deleted


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="actually delete; without it the script only reports",
    )
    parser.add_argument(
        "--visits",
        action="store_true",
        help=(
            "also trim the visit backlog to VISIT_RETENTION_DAYS, so both tables "
            "can be reclaimed by a single VACUUM FULL"
        ),
    )
    parser.add_argument("--batch-size", type=int, default=5000)
    parser.add_argument(
        "--retention-days",
        type=int,
        default=SETTINGS.VISIT_RETENTION_DAYS,
        help="visit retention window, only used with --visits",
    )
    args = parser.parse_args()

    conn = connect()
    try:
        users_deleted = purge_users(conn, args.batch_size, args.apply)
        visits_deleted = 0
        if args.visits:
            visits_deleted = purge_visits(
                conn, args.retention_days, args.batch_size, args.apply
            )

        with conn.cursor() as cur:
            report_sizes(cur, "after")
    finally:
        conn.close()

    if args.apply:
        print(f"deleted {users_deleted} users and {visits_deleted} visits")
        print(
            "the sizes above will barely move until you VACUUM FULL — "
            "the space is reusable, not returned to the filesystem"
        )


if __name__ == "__main__":
    main()
