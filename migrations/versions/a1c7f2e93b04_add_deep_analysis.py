"""Add deep analysis storage and its monthly counter

Hand-written: `flask db migrate` cannot run here, because src/extensions.py
resolves Google credentials at import time and there are none off-GCP. Revision
id is fixed rather than generated for the same reason.

Additive only — four new nullable columns, no rewrites of existing rows, no
constraints. `users` is the table that reached 86 MB before the anonymous-user
change, so adding a nullable column with no default is deliberate: Postgres 11+
adds it as a catalog-only change and never rewrites the table.

Revision ID: a1c7f2e93b04
Revises: 658d2ce7e681
Create Date: 2026-08-11

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1c7f2e93b04"
down_revision = "658d2ce7e681"
branch_labels = None
depends_on = None


def upgrade():
    # Mirrors monthly_voice_count / last_monthly_voice_reset exactly, so
    # get_monthly_deep_analysis_count() in utils.py can mirror the voice helper
    # rather than inventing a second reset scheme.
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("monthly_deep_analysis_count", sa.Integer(), nullable=True)
        )
        batch_op.add_column(
            sa.Column("last_monthly_deep_analysis_reset", sa.DateTime(), nullable=True)
        )

    with op.batch_alter_table("answer", schema=None) as batch_op:
        batch_op.add_column(sa.Column("deep_analysis", sa.JSON(), nullable=True))
        batch_op.add_column(
            sa.Column("deep_analysis_created_at", sa.DateTime(), nullable=True)
        )


def downgrade():
    with op.batch_alter_table("answer", schema=None) as batch_op:
        batch_op.drop_column("deep_analysis_created_at")
        batch_op.drop_column("deep_analysis")

    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("last_monthly_deep_analysis_reset")
        batch_op.drop_column("monthly_deep_analysis_count")
