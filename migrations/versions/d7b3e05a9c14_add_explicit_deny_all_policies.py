"""Add explicit deny-all policies

Revision ID: d7b3e05a9c14
Revises: c4e8a1d5f207
Create Date: 2026-08-19 16:41:18.902744

"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "d7b3e05a9c14"
down_revision = "c4e8a1d5f207"
branch_labels = None
depends_on = None

# c4e8a1d5f207 left every table with RLS on and no policies, which Supabase's
# Security Advisor reports as `rls_enabled_no_policy` (INFO, one per table). The
# state is deliberate, and Supabase's own guidance is to say so explicitly rather
# than leave it implied: "some users may enable RLS with no policies intentionally
# to restrict access over APIs. In those cases we recommend making that intent
# explicit with a rejection policy."
#
# Functionally this changes nothing. RLS with no policies already denies every
# non-bypass role, the anon/authenticated grants are gone, and `postgres` and
# `service_role` have rolbypassrls. It is worth doing anyway for two reasons:
# a reader can tell deny-all was chosen rather than forgotten, and unlike the
# REVOKEs a policy is part of the schema, so pg_dump --no-acl carries it into a
# restore.
TABLES = (
    "users",
    "answer",
    "visit",
    "feedback",
    "user_achievements",
    "alembic_version",
)

POLICY = "deny_all"


def upgrade():
    for table in TABLES:
        # FOR ALL with both USING and WITH CHECK: USING alone would leave INSERT
        # uncovered, since INSERT is checked against WITH CHECK rather than USING.
        op.execute(
            f'CREATE POLICY {POLICY} ON public."{table}" '
            "FOR ALL USING (false) WITH CHECK (false)"
        )


def downgrade():
    for table in TABLES:
        op.execute(f'DROP POLICY {POLICY} ON public."{table}"')
