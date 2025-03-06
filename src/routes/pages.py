import json
import os
import uuid
from datetime import datetime

import stripe
from flask import (
    Blueprint,
    current_app,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import current_user

from config import get_settings
from constants.achievements import ACHIEVEMENTS
from constants.levels import Level
from extensions import db, limiter
from models import Answer, Feedback, User
from services.level_service import get_level_info
from services.question_service import load_questions
from utils import (
    get_daily_evaluation_count,
    get_daily_voice_count,
    get_eval_limit,
    get_monthly_eval_limit,
    get_monthly_evaluation_count,
    get_monthly_voice_count,
    get_monthly_voice_limit,
    get_voice_limit,
)

pages_bp = Blueprint("pages", __name__)

SETTINGS = get_settings()


def calculate_valid_xp(answer):
    """Template filter to calculate actual XP earned considering relevance threshold"""
    total_xp = 0
    if (
        answer.evaluation_scores.get("Relevance", 0)
        >= SETTINGS.RELEVANCE_THRESHOLD_FOR_XP
    ):
        total_xp += answer.xp_earned

    if (
        answer.challenge_response
        and answer.challenge_evaluation_scores.get("Relevance", 0)
        >= SETTINGS.RELEVANCE_THRESHOLD_FOR_XP
    ):
        total_xp += answer.challenge_xp_earned

    return total_xp


# Register the template filter
@pages_bp.app_template_filter("calculate_valid_xp")
def calculate_valid_xp_filter(answer):
    return calculate_valid_xp(answer)


@pages_bp.route("/")
def home():
    if "user_id" not in session:
        session["user_id"] = str(uuid.uuid4())

    user = User.query.filter_by(uuid=session["user_id"]).first()
    if not user:
        user = User(uuid=session["user_id"], tier="anonymous")
        db.session.add(user)
        db.session.commit()

    level_info = get_level_info(user.xp)
    daily_eval_count = get_daily_evaluation_count(user.uuid)
    eval_limit = get_eval_limit(user.tier)
    daily_voice_count = get_daily_voice_count(user.uuid)
    voice_limit = get_voice_limit(user.tier)

    # Get monthly counts and limits
    monthly_eval_count = get_monthly_evaluation_count(user.uuid)
    monthly_eval_limit = get_monthly_eval_limit(user.tier)
    monthly_voice_count = get_monthly_voice_count(user.uuid)
    monthly_voice_limit = get_monthly_voice_limit(user.tier)

    # Get all achievements and user's earned achievements
    all_achievements = ACHIEVEMENTS
    earned_achievements = [
        achievement.achievement_id for achievement in user.achievements
    ]

    return render_template(
        "index.html",
        level_info=level_info,
        daily_eval_count=daily_eval_count,
        eval_limit=eval_limit,
        daily_voice_count=daily_voice_count,
        voice_limit=voice_limit,
        monthly_eval_count=monthly_eval_count,
        monthly_eval_limit=monthly_eval_limit,
        monthly_voice_count=monthly_voice_count,
        monthly_voice_limit=monthly_voice_limit,
        all_achievements=all_achievements,
        earned_achievements=earned_achievements,
    )


@pages_bp.route("/how_it_works")
def how_it_works():
    # First check for the query parameter; if not present, use the session language (default to "en")
    lang = request.args.get("lang") or session.get("language", "en")
    trans_file = os.path.join(
        current_app.root_path, "static", "translations", f"{lang}.json"
    )
    with open(trans_file, "r", encoding="utf-8") as f:
        translations = json.load(f)

    # Get the evaluation criteria from the translation file
    criteria = translations.get("evaluationCriteria", {})

    # Create a mapping for dimension translations
    dimension_mapping = {
        "Relevance": translations["evaluation"]["scores"]["relevance"],
        "Logical Structure": translations["evaluation"]["scores"]["logic"],
        "Clarity": translations["evaluation"]["scores"]["clarity"],
        "Depth": translations["evaluation"]["scores"]["depth"],
        "Objectivity": translations["evaluation"]["scores"]["objectivity"],
        "Creativity": translations["evaluation"]["scores"]["creativity"],
    }

    return render_template(
        "how_it_works.html",
        criteria=criteria,
        dimension_mapping=dimension_mapping,
        translations=translations,
    )


@pages_bp.route("/how_to_improve")
def how_to_improve():
    # Get language from query parameter or session (default to "en")
    lang = request.args.get("lang") or session.get("language", "en")
    trans_file = os.path.join(
        current_app.root_path, "static", "translations", f"{lang}.json"
    )

    with open(trans_file, "r", encoding="utf-8") as f:
        translations = json.load(f)

    # Get the page content from translations
    page_content = translations.get("howToImprovePage", {})

    # Ensure the translations are properly loaded
    if not page_content:
        # Fallback to English if the current language doesn't have the content
        fallback_file = os.path.join(
            current_app.root_path, "static", "translations", "en.json"
        )
        with open(fallback_file, "r", encoding="utf-8") as f:
            fallback_translations = json.load(f)
            page_content = fallback_translations.get("howToImprovePage", {})

    return render_template(
        "how_to_improve.html", page_content=page_content, translations=translations
    )


@pages_bp.route("/support")
def support():
    # Get language from query parameter or session (default to "en")
    lang = request.args.get("lang") or session.get("language", "en")
    trans_file = os.path.join(
        current_app.root_path, "static", "translations", f"{lang}.json"
    )

    with open(trans_file, "r", encoding="utf-8") as f:
        translations = json.load(f)

    # Get the page content from translations
    page_content = translations.get("supportPage", {})

    return render_template(
        "support.html", page_content=page_content, translations=translations
    )


@pages_bp.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("pages.home"))

    user = User.query.filter_by(uuid=session["user_id"]).first()
    if not user:
        return redirect(url_for("pages.home"))

    level_info = get_level_info(user.xp)
    daily_eval_count = get_daily_evaluation_count(user.uuid)
    eval_limit = get_eval_limit(user.tier)
    daily_voice_count = get_daily_voice_count(user.uuid)
    voice_limit = get_voice_limit(user.tier)

    # Get monthly counts and limits
    monthly_eval_count = get_monthly_evaluation_count(user.uuid)
    monthly_eval_limit = get_monthly_eval_limit(user.tier)
    monthly_voice_count = get_monthly_voice_count(user.uuid)
    monthly_voice_limit = get_monthly_voice_limit(user.tier)

    # Get all achievements and user's earned achievements
    all_achievements = ACHIEVEMENTS
    earned_achievements = [
        achievement.achievement_id for achievement in user.achievements
    ]

    # Query answers sorted by created_at descending and then by id descending to break ties
    answers = (
        Answer.query.filter_by(user_uuid=user.uuid)
        .order_by(Answer.created_at.desc(), Answer.id.desc())
        .all()
    )
    answers_dict = [answer.to_dict() for answer in answers]

    # Pre-compute level status flags
    levels_with_status = []
    for level in Level.all_levels:
        level_dict = {
            "id": level.id,
            "name": level.name,
            "display_name": level.display_name,
            "image_path": level.image_path,
            "is_unlocked": level.id <= level_info["level_number"],
            "is_current": level.id == level_info["level_number"],
            "is_completed": level.id < level_info["level_number"],
        }
        levels_with_status.append(level_dict)

    # Sync session XP with database.
    session["xp"] = user.xp

    return render_template(
        "profile.html",
        xp=user.xp,
        level_info=level_info,
        user=user,
        answers_json=answers_dict,
        daily_eval_count=daily_eval_count,
        eval_limit=eval_limit,
        daily_voice_count=daily_voice_count,
        voice_limit=voice_limit,
        monthly_eval_count=monthly_eval_count,
        monthly_eval_limit=monthly_eval_limit,
        monthly_voice_count=monthly_voice_count,
        monthly_voice_limit=monthly_voice_limit,
        all_achievements=all_achievements,
        earned_achievements=earned_achievements,
        all_levels=levels_with_status,
    )


@pages_bp.route("/subscription")
def subscription():
    """Render the subscription page with plan options."""
    if "user_id" not in session:
        return redirect(url_for("pages.home"))

    user = User.query.filter_by(uuid=session["user_id"]).first()
    if not user:
        return redirect(url_for("pages.home"))

    # Set up Stripe
    stripe.api_key = SETTINGS.STRIPE_SECRET_KEY

    return render_template(
        "subscription.html",
        user=user,
        SETTINGS=SETTINGS,
        stripe_public_key=SETTINGS.STRIPE_PUBLIC_KEY,
        current_year=datetime.now().year,
    )


@pages_bp.route("/create-checkout-session", methods=["POST"])
def create_checkout_session():
    """Create a Stripe checkout session for the selected plan."""
    if "user_id" not in session:
        return jsonify({"error": "User not authenticated"}), 401

    user = User.query.filter_by(uuid=session["user_id"]).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    # Set up Stripe
    stripe.api_key = SETTINGS.STRIPE_SECRET_KEY

    # Get the plan from the request
    data = request.json
    plan = data.get("plan")

    # Set price based on plan
    if plan == "plus":
        plan_name = "Plus"
        amount = 500  # $5.00
    elif plan == "pro":
        plan_name = "Pro"
        amount = 2000  # $20.00
    else:
        return jsonify({"error": "Invalid plan selected"}), 400

    try:
        # Create a checkout session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"ArguMentor {plan_name} Plan",
                            "description": f"Monthly subscription to ArguMentor {plan_name} Plan",
                        },
                        "unit_amount": amount,
                        "recurring": {
                            "interval": "month",
                        },
                    },
                    "quantity": 1,
                },
            ],
            mode="subscription",
            success_url=request.host_url
            + "subscription-success?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=request.host_url + "subscription",
            client_reference_id=user.uuid,
            metadata={
                "user_uuid": user.uuid,
                "plan": plan,
            },
        )

        return jsonify({"id": checkout_session.id})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@pages_bp.route("/subscription-success")
def subscription_success():
    """Handle successful subscription."""
    if "user_id" not in session:
        return redirect(url_for("pages.home"))

    session_id = request.args.get("session_id")
    if not session_id:
        return redirect(url_for("pages.subscription"))

    # Set up Stripe
    stripe.api_key = SETTINGS.STRIPE_SECRET_KEY

    try:
        # Retrieve the checkout session
        checkout_session = stripe.checkout.Session.retrieve(session_id)

        # Get the user and plan from the session metadata
        user_uuid = checkout_session.metadata.get("user_uuid")
        plan = checkout_session.metadata.get("plan")

        # Update the user's tier
        user = User.query.filter_by(uuid=user_uuid).first()
        if user and plan in ["plus", "pro"]:
            user.tier = plan
            db.session.commit()

        return render_template(
            "subscription_success.html",
            plan=plan.title(),
            user=user,
            current_year=datetime.now().year,
        )

    except Exception as e:
        current_app.logger.error(f"Error processing subscription success: {str(e)}")
        return redirect(url_for("pages.subscription"))


@pages_bp.route("/update-subscription", methods=["POST"])
def update_subscription():
    """Update user subscription to free tier."""
    if "user_id" not in session:
        return redirect(url_for("pages.home"))

    user = User.query.filter_by(uuid=session["user_id"]).first()
    if not user:
        return redirect(url_for("pages.home"))

    plan = request.form.get("plan")
    if plan == "free":
        user.tier = "free"
        db.session.commit()

    return redirect(url_for("pages.profile"))


@pages_bp.route("/stripe-webhook", methods=["POST"])
def stripe_webhook():
    """Handle Stripe webhook events."""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get("Stripe-Signature")

    # Set up Stripe
    stripe.api_key = SETTINGS.STRIPE_SECRET_KEY

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, SETTINGS.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload
        current_app.logger.error(f"Invalid Stripe payload: {str(e)}")
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        current_app.logger.error(f"Invalid Stripe signature: {str(e)}")
        return jsonify({"error": "Invalid signature"}), 400

    # Handle the event
    if event["type"] == "customer.subscription.updated":
        subscription = event["data"]["object"]
        user_uuid = subscription.metadata.get("user_uuid")

        if user_uuid:
            user = User.query.filter_by(uuid=user_uuid).first()
            if user:
                # Update user tier based on subscription status
                if subscription["status"] == "active":
                    # Get the plan from the subscription items
                    items = subscription["items"]["data"]
                    if items:
                        price_id = items[0]["price"]["id"]

                        if price_id == SETTINGS.STRIPE_PLUS_PRICE_ID:
                            user.tier = "plus"
                        elif price_id == SETTINGS.STRIPE_PRO_PRICE_ID:
                            user.tier = "pro"

                        db.session.commit()
                elif subscription["status"] in ["canceled", "unpaid"]:
                    user.tier = "free"
                    db.session.commit()

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        user_uuid = subscription.metadata.get("user_uuid")

        if user_uuid:
            user = User.query.filter_by(uuid=user_uuid).first()
            if user:
                user.tier = "free"
                db.session.commit()

    return jsonify({"status": "success"})


@pages_bp.route("/submit_feedback", methods=["GET", "POST"])
@limiter.limit(
    SETTINGS.SUBMISSION_RATE_LIMITS,
    error_message="Too many submissions. Please wait before trying again.",
)
def submit_feedback():
    if request.method == "GET":
        return redirect(url_for("pages.support", show_feedback=True))

    try:
        if not request.is_json:
            return jsonify({"error": "Content-Type must be application/json"}), 400

        data = request.json
        message = data.get("message", "").strip()
        category = data.get("category", "").strip()

        if not message or not category:
            return jsonify({"error": "Message and category are required"}), 400

        feedback = Feedback(
            user_uuid=session.get("user_id"), message=message, category=category
        )

        db.session.add(feedback)
        db.session.commit()

        return jsonify({"success": True})
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        db.session.remove()


@pages_bp.route("/set_language", methods=["POST"])
def set_language():
    if not request.is_json:
        return jsonify({"error": "Content-Type must be application/json"}), 400

    data = request.get_json()
    language = data.get("language")

    if language in ["en", "de"]:
        session["language"] = language
        load_questions()
        # If logged in, persist language preference in the user's account.
        if current_user.is_authenticated:
            current_user.preferred_language = language
            db.session.commit()
        return jsonify({"status": "success"})

    return jsonify({"status": "error", "message": "Invalid language"}), 400


@pages_bp.route("/privacy")
def privacy():
    return render_template("privacy.html")


@pages_bp.route("/terms")
def terms():
    return render_template("terms.html")


@pages_bp.route("/contact")
def contact():
    return render_template("contact.html")
