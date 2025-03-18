import os
from datetime import UTC, datetime, timedelta

import click

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
        user_identifier = click.prompt(
            "Enter user identifier(s) (email, username, or UUID) - comma-separated for multiple users"
        )
        tier = click.prompt(
            "Enter target tier",
            type=click.Choice(["free", "plus", "pro"], case_sensitive=False),
        )

        duration_months = None
        if tier in ["plus", "pro"]:
            duration_months = click.prompt(
                "Enter subscription duration in months (0 for indefinite)",
                type=int,
                default=12,
            )

        # Split user identifiers if multiple were provided
        user_identifiers = [id.strip() for id in user_identifier.split(",")]

        successful_upgrades = 0
        failed_upgrades = 0

        for single_user_identifier in user_identifiers:
            # Find the user
            user = None
            if single_user_identifier:
                user = User.query.filter_by(uuid=single_user_identifier).first()
                if not user:
                    user = User.query.filter_by(email=single_user_identifier).first()
                if not user:
                    user = User.query.filter_by(username=single_user_identifier).first()

            if not user:
                click.echo(
                    f"Error: User not found with identifier: {single_user_identifier}"
                )
                failed_upgrades += 1
                continue

            # Store the old tier for logging
            old_tier = user.tier

            # Update the user's tier
            user.tier = tier

            # Set subscription_end_date based on the duration
            if tier in ["plus", "pro"]:
                if duration_months == 0:
                    # Indefinite subscription - set to None
                    user.subscription_end_date = None
                else:
                    # Set to the specified number of months from now
                    user.subscription_end_date = datetime.now(UTC) + timedelta(
                        days=30 * duration_months
                    )

                user.is_subscription_canceled = False
                user.pending_plan_change = None
            else:
                # Free tier has no end date
                user.subscription_end_date = None

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
                f"  Subscription End Date: {user.subscription_end_date.isoformat() if user.subscription_end_date else 'Indefinite'}"
            )
            click.echo("")

            successful_upgrades += 1

        if len(user_identifiers) > 1:
            click.echo(
                f"Summary: {successful_upgrades} users upgraded successfully, {failed_upgrades} failed."
            )

    @app.cli.command("list_users")
    @click.option("--all", is_flag=True, help="Show all users including anonymous tier")
    @click.option(
        "--tier",
        type=click.Choice(["anonymous", "free", "plus", "pro"], case_sensitive=False),
        help="Filter users by specific tier",
    )
    def list_users_command(all, tier):
        """List all users in the system.

        flask list_users - Lists all non-anonymous users
        flask list_users --all - Lists all users including anonymous tier
        flask list_users --tier plus - Lists only users on the "plus" tier

        """
        # Retrieve all users first
        with app.app_context():
            all_users = User.query.all()

            # Apply filters manually
            if tier:
                # Filter by specific tier
                users = [
                    user for user in all_users if user.tier.lower() == tier.lower()
                ]
            elif not all:
                # Exclude anonymous users
                users = [user for user in all_users if user.tier != "anonymous"]
            else:
                # Show all users
                users = all_users

            if not users:
                if tier:
                    click.echo(f"No users found with tier: {tier}")
                elif all:
                    click.echo("No users found in the database.")
                else:
                    click.echo("No non-anonymous users found in the database.")
                return

            # Prepare filter description for output
            filter_desc = ""
            if tier:
                filter_desc = f" with tier '{tier}'"
            elif not all:
                filter_desc = " (excluding anonymous tier)"

            click.echo(f"Found {len(users)} users{filter_desc}:")
            for user in users:
                click.echo(f"UUID: {user.uuid}")
                click.echo(f"  Username: {user.username}")
                click.echo(f"  Email: {user.email or 'N/A'}")
                click.echo(f"  Tier: {user.tier}")
                click.echo(
                    f"  Subscription End Date: {user.subscription_end_date.isoformat() if user.subscription_end_date else 'N/A'}"
                )
                click.echo("")
