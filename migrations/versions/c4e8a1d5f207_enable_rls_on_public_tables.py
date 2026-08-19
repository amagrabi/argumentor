"""Enable RLS on public tables

Revision ID: c4e8a1d5f207
Revises: a1c7f2e93b04
Create Date: 2026-08-19 10:12:04.331207

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "c4e8a1d5f207"
down_revision = "a1c7f2e93b04"
branch_labels = None
depends_on = None

# Supabase's Security Advisor flags every one of these as `rls_disabled_in_public`.
# The project's Data API is live (an unauthenticated GET to /rest/v1/users returns
# 401 "No API key found", so PostgREST is listening), and Supabase's default
# privileges had granted anon and authenticated full SELECT/INSERT/UPDATE/DELETE/
# TRUNCATE on all of them. Nothing but possession of the publishable anon key stood
# between the internet and the users table.
#
# This app never uses PostgREST — it talks to Postgres as `postgres` over the
# session pooler via SQLAlchemy — so denying the API roles costs nothing.
TABLES = (
    "users",
    "answer",
    "visit",
    "feedback",
    "user_achievements",
    "alembic_version",
)


def upgrade():
    for table in TABLES:
        # Safe for the app, and for this migration writing to alembic_version:
        # `postgres` and `service_role` both have rolbypassrls, verified against
        # the live database. With RLS on and no policies, anon and authenticated
        # are denied instead.
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')
        # Belt and braces, so the tables are not merely policy-less but ungranted.
        # This half does *not* survive a restore — scripts/backup_db.py dumps with
        # --no-acl, which omits GRANT/REVOKE, while ENABLE ROW LEVEL SECURITY is
        # part of the table definition and is dumped. Hence both.
        op.execute(f'REVOKE ALL ON public."{table}" FROM anon, authenticated')


def downgrade():
    for table in TABLES:
        op.execute(f'GRANT ALL ON public."{table}" TO anon, authenticated')
        op.execute(f'ALTER TABLE public."{table}" DISABLE ROW LEVEL SECURITY')
