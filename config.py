import os

from dotenv import load_dotenv

# Automatically load the variables from the .env file into os.environ
load_dotenv()


class Config:
    SECRET_KEY = os.getenv("SECRET_KEY", "fallback-secret-key")
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URI", "sqlite:///argumentor.db")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
