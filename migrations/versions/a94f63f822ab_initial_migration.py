"""Initial migration

Revision ID: a94f63f822ab
Revises:
Create Date: 2025-02-14 16:38:05.144691

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "a94f63f822ab"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.drop_table("user")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    op.create_table(
        "user",
        sa.Column("uuid", sa.VARCHAR(length=36), nullable=False),
        sa.Column("username", sa.VARCHAR(length=255), nullable=True),
        sa.Column("xp", sa.INTEGER(), nullable=True),
        sa.Column("created_at", sa.DATETIME(), nullable=True),
        sa.Column("email", sa.VARCHAR(length=255), nullable=True),
        sa.Column("password_hash", sa.VARCHAR(length=255), nullable=True),
        sa.Column("google_id", sa.VARCHAR(length=255), nullable=True),
        sa.Column("is_active", sa.BOOLEAN(), nullable=True),
        sa.Column("profile_pic", sa.VARCHAR(length=512), nullable=True),
        sa.Column("category_preferences", sa.TEXT(), nullable=True),
        sa.PrimaryKeyConstraint("uuid"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("google_id"),
        sa.UniqueConstraint("username"),
    )
    # ### end Alembic commands ###
