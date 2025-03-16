"""increase_user_agent_length

Revision ID: 658d2ce7e681
Revises: 0208681c3092
Create Date: 2025-03-16 12:51:12.544966

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "658d2ce7e681"
down_revision = "0208681c3092"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("visit", schema=None) as batch_op:
        batch_op.alter_column(
            "user_agent",
            existing_type=sa.VARCHAR(length=200),
            type_=sa.String(length=500),
            existing_nullable=True,
        )

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("visit", schema=None) as batch_op:
        batch_op.alter_column(
            "user_agent",
            existing_type=sa.String(length=500),
            type_=sa.VARCHAR(length=200),
            existing_nullable=True,
        )

    # ### end Alembic commands ###
