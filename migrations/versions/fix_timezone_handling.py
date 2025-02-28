"""fix timezone handling

Revision ID: fix_timezone_handling
Revises: 4276ee13eff7
Create Date: 2025-02-28 15:55:00.000000

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "fix_timezone_handling"
down_revision = "4276ee13eff7"  # Point to the previous migration
branch_labels = None
depends_on = None


def upgrade():
    # Add timezone info to existing datetime columns
    conn = op.get_bind()

    # Check and update users table
    if conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users')"
        )
    ).scalar():
        op.execute("""
            UPDATE users
            SET created_at = created_at AT TIME ZONE 'UTC'
            WHERE created_at IS NOT NULL;

            UPDATE users
            SET reset_token_expiry = reset_token_expiry AT TIME ZONE 'UTC'
            WHERE reset_token_expiry IS NOT NULL;

            UPDATE users
            SET last_voice_transcription = last_voice_transcription AT TIME ZONE 'UTC'
            WHERE last_voice_transcription IS NOT NULL;
        """)

    # Check and update answers table
    if conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'answers')"
        )
    ).scalar():
        op.execute("""
            UPDATE answers
            SET created_at = created_at AT TIME ZONE 'UTC'
            WHERE created_at IS NOT NULL;
        """)

    # Check and update visits table
    if conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'visits')"
        )
    ).scalar():
        op.execute("""
            UPDATE visits
            SET created_at = created_at AT TIME ZONE 'UTC'
            WHERE created_at IS NOT NULL;
        """)

    # Check and update feedback table
    if conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'feedback')"
        )
    ).scalar():
        op.execute("""
            UPDATE feedback
            SET created_at = created_at AT TIME ZONE 'UTC'
            WHERE created_at IS NOT NULL;
        """)

    # Check and update user_achievements table
    if conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_achievements')"
        )
    ).scalar():
        op.execute("""
            UPDATE user_achievements
            SET earned_at = earned_at AT TIME ZONE 'UTC'
            WHERE earned_at IS NOT NULL;
        """)


def downgrade():
    # Remove timezone info from datetime columns
    conn = op.get_bind()

    # Check and update users table
    if conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'users')"
        )
    ).scalar():
        op.execute("""
            UPDATE users
            SET created_at = created_at AT TIME ZONE 'UTC'
            WHERE created_at IS NOT NULL;

            UPDATE users
            SET reset_token_expiry = reset_token_expiry AT TIME ZONE 'UTC'
            WHERE reset_token_expiry IS NOT NULL;

            UPDATE users
            SET last_voice_transcription = last_voice_transcription AT TIME ZONE 'UTC'
            WHERE last_voice_transcription IS NOT NULL;
        """)

    # Check and update answers table
    if conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'answers')"
        )
    ).scalar():
        op.execute("""
            UPDATE answers
            SET created_at = created_at AT TIME ZONE 'UTC'
            WHERE created_at IS NOT NULL;
        """)

    # Check and update visits table
    if conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'visits')"
        )
    ).scalar():
        op.execute("""
            UPDATE visits
            SET created_at = created_at AT TIME ZONE 'UTC'
            WHERE created_at IS NOT NULL;
        """)

    # Check and update feedback table
    if conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'feedback')"
        )
    ).scalar():
        op.execute("""
            UPDATE feedback
            SET created_at = created_at AT TIME ZONE 'UTC'
            WHERE created_at IS NOT NULL;
        """)

    # Check and update user_achievements table
    if conn.execute(
        sa.text(
            "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'user_achievements')"
        )
    ).scalar():
        op.execute("""
            UPDATE user_achievements
            SET earned_at = earned_at AT TIME ZONE 'UTC'
            WHERE earned_at IS NOT NULL;
        """)
