import uuid
from datetime import UTC, datetime

from flask_login import UserMixin

from extensions import db


class User(db.Model, UserMixin):
    __tablename__ = "users"

    uuid = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    username = db.Column(db.String(255), unique=True, nullable=False)
    preferred_language = db.Column(db.String(2), default="en")
    xp = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    tier = db.Column(db.String(20), nullable=False, default="anonymous")
    answers = db.relationship(
        "Answer", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    email = db.Column(db.String(255), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    profile_pic = db.Column(db.String(512), nullable=True)
    reset_token = db.Column(db.String(100), unique=True, nullable=True)
    reset_token_expiry = db.Column(db.DateTime, nullable=True)
    category_preferences = db.Column(db.Text, nullable=True)
    visits = db.relationship(
        "Visit", backref="user", lazy=True, cascade="all, delete-orphan"
    )
    feedback = db.relationship(
        "Feedback", backref="user", lazy=True, cascade="all, delete-orphan"
    )

    def get_id(self):
        return str(self.uuid)

    def __repr__(self):
        return f"<User {self.uuid} {self.username}>"


class Answer(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_uuid = db.Column(
        db.String(36), db.ForeignKey("users.uuid", ondelete="CASCADE"), nullable=False
    )
    question_id = db.Column(db.String(50), nullable=True)
    question_text = db.Column(db.Text, nullable=True)
    claim = db.Column(db.Text, nullable=False)
    argument = db.Column(db.Text, nullable=False)
    counterargument = db.Column(db.Text, nullable=True)
    evaluation_scores = db.Column(db.JSON, default=dict, nullable=False)
    evaluation_feedback = db.Column(db.JSON, default=dict, nullable=False)
    xp_earned = db.Column(db.Integer, nullable=False)

    # Challenge refinement feature:
    challenge = db.Column(
        db.Text, nullable=True
    )  # The LLM–generated challenge text for the original argument
    challenge_response = db.Column(
        db.Text, nullable=True
    )  # The user's response to the challenge
    challenge_evaluation_scores = db.Column(db.JSON, default=dict, nullable=False)
    challenge_evaluation_feedback = db.Column(db.JSON, default=dict, nullable=False)
    challenge_xp_earned = db.Column(db.Integer, nullable=False, default=0)

    created_at = db.Column(db.DateTime, default=datetime.now(UTC))

    input_mode = db.Column(db.String(10), nullable=True)  # "text" or "voice"

    __table_args__ = (db.Index("ix_user_question", "user_uuid", "question_id"),)

    def __repr__(self):
        return f"<Answer {self.id} for user {self.user_uuid}>"

    def to_dict(self):
        return {
            "id": self.id,
            "question_text": self.question_text,
            "claim": self.claim,
            "argument": self.argument,
            "counterargument": self.counterargument,
            "evaluation_scores": self.evaluation_scores,
            "evaluation_feedback": self.evaluation_feedback,
            "xp_earned": self.xp_earned,
            "challenge": self.challenge,
            "challenge_response": self.challenge_response,
            "challenge_evaluation_scores": self.challenge_evaluation_scores,
            "challenge_evaluation_feedback": self.challenge_evaluation_feedback,
            "challenge_xp_earned": self.challenge_xp_earned,
            "created_at": self.created_at.isoformat(),
        }


class Visit(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_uuid = db.Column(
        db.String(36), db.ForeignKey("users.uuid", ondelete="CASCADE"), nullable=True
    )
    ip_address = db.Column(db.String(45), nullable=True)
    user_agent = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))

    def __repr__(self):
        return f"<Visit {self.id}: {self.ip_address} at {self.created_at}>"


class Feedback(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_uuid = db.Column(
        db.String(36), db.ForeignKey("users.uuid", ondelete="CASCADE"), nullable=True
    )
    message = db.Column(db.Text, nullable=False)
    category = db.Column(
        db.String(50), nullable=False
    )  # e.g., 'bug', 'feature', 'general'
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))

    def __repr__(self):
        return f"<Feedback {self.id}>"
