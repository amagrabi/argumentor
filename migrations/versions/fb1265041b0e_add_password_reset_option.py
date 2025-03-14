"""Add password reset option

Revision ID: fb1265041b0e
Revises: ebb1cab3bea4
Create Date: 2025-02-16 23:28:02.429864

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fb1265041b0e"
down_revision = "ebb1cab3bea4"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("reset_token", sa.String(length=100), nullable=True)
        )
        batch_op.add_column(
            sa.Column("reset_token_expiry", sa.DateTime(), nullable=True)
        )
        batch_op.create_unique_constraint(None, ["reset_token"])

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_constraint(None, type_="unique")
        batch_op.drop_column("reset_token_expiry")
        batch_op.drop_column("reset_token")

    # ### end Alembic commands ###
