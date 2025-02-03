from datetime import datetime

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False)
    xp = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    # You can add other fields here (e.g. username, email) as needed.
    answers = db.relationship("Answer", backref="user", lazy=True)

    def __repr__(self):
        return f"<User {self.uuid}>"


class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    question_id = db.Column(db.String(50), nullable=True)
    question_text = db.Column(db.Text, nullable=True)
    answer_text = db.Column(db.Text, nullable=False)
    # Store ratings per dimension as a JSON object, e.g. {"Clarity": 7, ...}
    evaluation_scores = db.Column(db.JSON, nullable=False)
    # Store LLM explanations as a JSON object, e.g. {"Clarity": "Your points are clear…", ...}
    evaluation_feedback = db.Column(db.JSON, nullable=False)
    xp_earned = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Answer {self.id} from user {self.user_id}>"
