import uuid
from datetime import UTC, datetime

from flask_login import UserMixin

from extensions import db


class User(db.Model, UserMixin):
    uuid = db.Column(db.String(36), primary_key=True)
    xp = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))
    answers = db.relationship("Answer", backref="user", lazy=True)
    email = db.Column(db.String(255), unique=True, nullable=True)
    password_hash = db.Column(db.String(255), nullable=True)
    google_id = db.Column(db.String(255), unique=True, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    profile_pic = db.Column(db.String(512), nullable=True)

    def get_id(self):
        return str(self.uuid)

    def __repr__(self):
        return f"<User {self.uuid}>"


class Answer(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_uuid = db.Column(db.String(36), db.ForeignKey("user.uuid"), nullable=False)
    question_id = db.Column(db.String(50), nullable=True)
    question_text = db.Column(db.Text, nullable=True)
    claim = db.Column(db.Text, nullable=False)
    argument = db.Column(db.Text, nullable=False)
    counterargument = db.Column(db.Text, nullable=True)
    evaluation_scores = db.Column(db.JSON, default=dict, nullable=False)
    evaluation_feedback = db.Column(db.JSON, default=dict, nullable=False)
    xp_earned = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))

    __table_args__ = (db.Index("ix_user_question", "user_uuid", "question_id"),)

    def __repr__(self):
        return f"<Answer {self.id} for user {self.user_uuid}>"


class Visit(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_uuid = db.Column(db.String(36), db.ForeignKey("user.uuid"), nullable=True)
    ip_address = db.Column(db.String(45))  # Supports IPv6 addresses
    user_agent = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.now(UTC))

    def __repr__(self):
        return f"<Visit {self.id}: {self.ip_address} at {self.created_at}>"
