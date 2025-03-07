"""Add achievements

Revision ID: 025a4c3b252a
Revises: f3d4660f348a
Create Date: 2025-02-24 15:03:22.613969

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "025a4c3b252a"
down_revision = "f3d4660f348a"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "achievements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False),
        sa.Column("icon", sa.String(length=100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_table(
        "user_achievements",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_uuid", sa.String(length=36), nullable=False),
        sa.Column("achievement_id", sa.Integer(), nullable=False),
        sa.Column("achieved_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(
            ["achievement_id"],
            ["achievements.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_uuid"],
            ["users.uuid"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("user_achievements")
    op.drop_table("achievements")
    # ### end Alembic commands ###
