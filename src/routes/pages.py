import os
import uuid
from datetime import datetime

import yaml
from flask import Blueprint, current_app, redirect, render_template, session, url_for
from flask_login import current_user

from extensions import db
from models import User
from services.leveling import get_level_info

pages_bp = Blueprint("pages", __name__)


@pages_bp.route("/")
def home():
    # Use the authenticated user's ID if logged in
    if current_user.is_authenticated:
        user = current_user
        session["user_id"] = current_user.uuid  # Sync session with logged-in user
    else:
        # Existing anonymous user handling
        if "user_id" not in session:
            session["user_id"] = str(uuid.uuid4())
        user = User.query.filter_by(uuid=session["user_id"]).first()
        if not user:
            user = User(uuid=session["user_id"], xp=0)
            db.session.add(user)
            db.session.commit()

    xp = user.xp
    level_info = get_level_info(xp)
    # ... rest of the function remains the same
    xp = user.xp
    level_info = get_level_info(xp)

    # Load and select the bias of the day from the YAML file
    biases_path = os.path.join(current_app.root_path, "data", "cognitive_biases.yaml")
    with open(biases_path, "r") as f:
        biases_data = yaml.safe_load(f)
    biases = biases_data.get("cognitive_biases", [])
    if biases:
        day_of_year = datetime.now().timetuple().tm_yday
        bias_index = day_of_year % len(biases)
        bias = biases[bias_index]
    else:
        bias = {"name": "N/A", "description": "", "example": ""}

    return render_template("index.html", xp=xp, level_info=level_info, bias=bias)


@pages_bp.route("/how_it_works")
def how_it_works():
    criteria_path = os.path.join(
        current_app.root_path, "data", "evaluation_criteria.yaml"
    )
    with open(criteria_path, "r") as f:
        criteria = yaml.safe_load(f)
    return render_template("how_it_works.html", criteria=criteria)


@pages_bp.route("/reasoning_guide")
def reasoning_guide():
    data_path = os.path.join(current_app.root_path, "data", "cognitive_biases.yaml")
    with open(data_path, "r") as f:
        biases_data = yaml.safe_load(f)
    biases = biases_data.get("cognitive_biases", [])
    return render_template("reasoning_guide.html", biases=biases)


@pages_bp.route("/support")
def support():
    return render_template("support.html")


@pages_bp.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("pages.home"))

    user = User.query.filter_by(uuid=session["user_id"]).first()
    if not user:
        return redirect(url_for("pages.home"))

    level_info = get_level_info(user.xp)
    # Convert answers to dictionaries for JSON serialization
    answers_dict = [answer.to_dict() for answer in user.answers]
    # Sync session XP with database
    session["xp"] = user.xp
    return render_template(
        "profile.html",
        xp=user.xp,
        level_info=level_info,
        user=user,
        answers_json=answers_dict,
    )
