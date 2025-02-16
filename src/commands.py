import os

from models import db


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
