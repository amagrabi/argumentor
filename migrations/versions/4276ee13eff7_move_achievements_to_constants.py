"""Move achievements to constants

Revision ID: 4276ee13eff7
Revises: 025a4c3b252a
Create Date: 2025-02-24 17:45:26.092058

"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "4276ee13eff7"
down_revision = "025a4c3b252a"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("user_achievements", schema=None) as batch_op:
        batch_op.drop_constraint(
            "user_achievements_achievement_id_fkey", type_="foreignkey"
        )
        batch_op.add_column(sa.Column("earned_at", sa.DateTime(), nullable=True))
        batch_op.alter_column(
            "achievement_id",
            existing_type=sa.INTEGER(),
            type_=sa.String(length=50),
            existing_nullable=False,
        )
        batch_op.drop_column("achieved_at")

    op.drop_table("achievements")
    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("user_achievements", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column(
                "achieved_at",
                postgresql.TIMESTAMP(),
                autoincrement=False,
                nullable=True,
            )
        )
        batch_op.create_foreign_key(
            "user_achievements_achievement_id_fkey",
            "achievements",
            ["achievement_id"],
            ["id"],
        )
        batch_op.alter_column(
            "achievement_id",
            existing_type=sa.String(length=50),
            type_=sa.INTEGER(),
            existing_nullable=False,
        )
        batch_op.drop_column("earned_at")

    op.create_table(
        "achievements",
        sa.Column("id", sa.INTEGER(), autoincrement=True, nullable=False),
        sa.Column("code", sa.VARCHAR(length=50), autoincrement=False, nullable=False),
        sa.Column("name", sa.VARCHAR(length=100), autoincrement=False, nullable=False),
        sa.Column(
            "description", sa.VARCHAR(length=255), autoincrement=False, nullable=False
        ),
        sa.Column("icon", sa.VARCHAR(length=100), autoincrement=False, nullable=False),
        sa.Column(
            "created_at", postgresql.TIMESTAMP(), autoincrement=False, nullable=True
        ),
        sa.PrimaryKeyConstraint("id", name="achievements_pkey"),
        sa.UniqueConstraint("code", name="achievements_code_key"),
    )
    # ### end Alembic commands ###
