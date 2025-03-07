import os
from datetime import UTC, datetime, timedelta

from models import User, db


def register_commands(app):
    @app.cli.command("recreate_db")
    def recreate_db():
        """Drop and recreate the database"""
        instance_path = app.instance_path
        os.makedirs(instance_path, exist_ok=True)
        with app.app_context():
            db.drop_all()
            db.create_all()
        print("Database recreated!")

    @app.cli.command("drop_db")
    def drop_db():
        """Drop the database tables."""
        instance_path = app.instance_path
        os.makedirs(instance_path, exist_ok=True)
        with app.app_context():
            db.drop_all()
        print("Database dropped!")

    @app.cli.command("upgrade_user")
    def upgrade_user_command():
        """Upgrade a user to a specific tier without payment."""
        import click

        user_identifier = click.prompt(
            "Enter user identifier (email, username, or UUID)"
        )
        tier = click.prompt(
            "Enter target tier",
            type=click.Choice(["free", "plus", "pro"], case_sensitive=False),
        )

        # Find the user
        user = None
        if user_identifier:
            user = User.query.filter_by(uuid=user_identifier).first()
            if not user:
                user = User.query.filter_by(email=user_identifier).first()
            if not user:
                user = User.query.filter_by(username=user_identifier).first()

        if not user:
            click.echo(f"Error: User not found with identifier: {user_identifier}")
            return

        # Store the old tier for logging
        old_tier = user.tier

        # Update the user's tier
        user.tier = tier

        # If upgrading to a paid tier, set subscription_end_date to a year from now
        if tier in ["plus", "pro"]:
            user.subscription_end_date = datetime.now(UTC) + timedelta(days=365)
            user.is_subscription_canceled = False
            user.pending_plan_change = None

        db.session.commit()

        click.echo(
            f"Successfully upgraded user {user.username} from {old_tier} to {tier}"
        )
        click.echo("User details:")
        click.echo(f"  UUID: {user.uuid}")
        click.echo(f"  Username: {user.username}")
        click.echo(f"  Email: {user.email or 'N/A'}")
        click.echo(f"  Current Tier: {user.tier}")
        click.echo(
            f"  Subscription End Date: {user.subscription_end_date.isoformat() if user.subscription_end_date else 'N/A'}"
        )

    @app.cli.command("list_users")
    def list_users_command():
        """List all users in the system."""
        import click

        users = User.query.all()

        if not users:
            click.echo("No users found in the database.")
            return

        click.echo(f"Found {len(users)} users:")
        for user in users:
            click.echo(f"UUID: {user.uuid}")
            click.echo(f"  Username: {user.username}")
            click.echo(f"  Email: {user.email or 'N/A'}")
            click.echo(f"  Tier: {user.tier}")
            click.echo(
                f"  Subscription End Date: {user.subscription_end_date.isoformat() if user.subscription_end_date else 'N/A'}"
            )
            click.echo("")
