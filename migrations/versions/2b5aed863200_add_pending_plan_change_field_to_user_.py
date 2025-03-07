"""Add pending_plan_change field to User model

Revision ID: 2b5aed863200
Revises: f4a6b92d6b59
Create Date: 2025-03-06 20:53:19.241167

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "2b5aed863200"
down_revision = "f4a6b92d6b59"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("pending_plan_change", sa.String(length=20), nullable=True)
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("pending_plan_change")

    # ### end Alembic commands ###
