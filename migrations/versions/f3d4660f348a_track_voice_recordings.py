"""Track voice recordings

Revision ID: f3d4660f348a
Revises: fb85b50c3b2c
Create Date: 2025-02-19 18:51:08.072118

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "f3d4660f348a"
down_revision = "fb85b50c3b2c"
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.add_column(
            sa.Column("last_voice_transcription", sa.DateTime(), nullable=True)
        )
        batch_op.add_column(sa.Column("daily_voice_count", sa.Integer(), nullable=True))

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table("users", schema=None) as batch_op:
        batch_op.drop_column("daily_voice_count")
        batch_op.drop_column("last_voice_transcription")

    # ### end Alembic commands ###
