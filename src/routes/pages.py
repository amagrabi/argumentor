import hmac
import json
import logging
import os
from datetime import UTC, datetime, timedelta

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
from flask_mail import Message

from config import get_settings
from constants.achievements import ACHIEVEMENTS
from constants.levels import Level
from extensions import db, limiter
from models import Answer, Feedback, User, Visit
from routes.password_reset import mail
from services.achievement_service import get_question_category
from services.level_service import get_level_info
from services.question_service import load_questions
from services.user_service import (
    get_session_user,
    load_session_user,
    persist_session_user,
)
from utils import (
    get_daily_evaluation_count,
    get_daily_voice_count,
    get_eval_limit,
    get_monthly_deep_analysis_count,
    get_monthly_deep_analysis_limit,
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


# Register the calculate_valid_xp function as a template filter
@pages_bp.app_template_filter("calculate_valid_xp")
def calculate_valid_xp_filter(answer):
    return calculate_valid_xp(answer)


@pages_bp.route("/")
@pages_bp.route("/<lang>")
def home(lang=None):
    is_language_redirect = False
    if lang:
        if lang not in ["en", "de"]:
            return redirect(url_for("pages.home"))
        session["language"] = lang
        is_language_redirect = True
        if current_user.is_authenticated:
            current_user.preferred_language = lang
            db.session.commit()

    # Check if this is marked as a first-time visit after language redirect
    is_first_time_visit = session.pop("is_first_time_visit", False)

    # For language redirects, we'll let the client-side code determine
    # if the user is a first-time visitor based on localStorage
    is_language_redirect = True if is_first_time_visit else is_language_redirect

    # Check if we should show the login modal
    show_login = request.args.get("show_login") == "true"

    # Rendering the home page is not an action worth a database row — this is the
    # page every crawler that follows a link lands on. get_session_user() returns
    # an unsaved placeholder for a visitor who has never done anything, which
    # renders identically to the empty row it used to create here.
    user = get_session_user()

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

    # Deep analysis is Plus/Pro only, and the button is rendered only for those
    # tiers, so the count is looked up only where it can be shown. The counter
    # helper writes on reset, and rendering the home page has to stay read-only
    # for a visitor who has no users row.
    monthly_deep_analysis_limit = get_monthly_deep_analysis_limit(user.tier)
    monthly_deep_analysis_count = (
        get_monthly_deep_analysis_count(user.uuid) if monthly_deep_analysis_limit else 0
    )

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
        monthly_deep_analysis_count=monthly_deep_analysis_count,
        monthly_deep_analysis_limit=monthly_deep_analysis_limit,
        all_achievements=all_achievements,
        earned_achievements=earned_achievements,
        user=user,
        is_language_redirect=is_language_redirect,
        char_limits={
            "claim": SETTINGS.MAX_CLAIM,
            "argument": SETTINGS.MAX_ARGUMENT,
            "counterargument": SETTINGS.MAX_COUNTERARGUMENT,
            "voice": SETTINGS.MAX_VOICE_ANSWER,
            "challenge": SETTINGS.MAX_CHALLENGE_RESPONSE,
        },
        show_login=show_login,
    )


@pages_bp.route("/<lang>/how_it_works")
@pages_bp.route("/how_it_works")
def how_it_works(lang=None):
    if lang:
        if lang not in ["en", "de"]:
            return redirect(url_for("pages.how_it_works"))
        session["language"] = lang
        if current_user.is_authenticated:
            current_user.preferred_language = lang
            db.session.commit()

    # First check for the query parameter; if not present, use the session language (default to "en")
    lang = session.get("language", "en")
    trans_file = os.path.join(
        current_app.root_path, "static", "translations", f"{lang}.json"
    )
    with open(trans_file, "r", encoding="utf-8") as f:
        translations = json.load(f)

    # Get the evaluation criteria from the translation file
    criteria = translations.get("evaluationCriteria", {})

    # Create a mapping for dimension translations based on language
    if lang == "de":
        # For German, use the German keys from the translation file
        dimension_mapping = {
            "Relevanz": translations["evaluation"]["scores"]["relevance"],
            "Logische Struktur": translations["evaluation"]["scores"]["logic"],
            "Klarheit": translations["evaluation"]["scores"]["clarity"],
            "Tiefe": translations["evaluation"]["scores"]["depth"],
            "Objektivität": translations["evaluation"]["scores"]["objectivity"],
            "Kreativität": translations["evaluation"]["scores"]["creativity"],
        }
    else:
        # For English and other languages, use the English keys
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


@pages_bp.route("/<lang>/how_to_improve")
@pages_bp.route("/how_to_improve")
def how_to_improve(lang=None):
    if lang:
        if lang not in ["en", "de"]:
            return redirect(url_for("pages.how_to_improve"))
        session["language"] = lang
        if current_user.is_authenticated:
            current_user.preferred_language = lang
            db.session.commit()

    # Get language from session (default to "en")
    lang = session.get("language", "en")
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


@pages_bp.route("/<lang>/support")
@pages_bp.route("/support")
def support(lang=None):
    if lang:
        if lang not in ["en", "de"]:
            return redirect(url_for("pages.support"))
        session["language"] = lang
        if current_user.is_authenticated:
            current_user.preferred_language = lang
            db.session.commit()

    # Get language from session (default to "en")
    lang = session.get("language", "en")
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

    # An anonymous visitor who has submitted nothing has no row, and gets the
    # same empty profile their placeholder row used to give them.
    user = get_session_user()

    # Get language from query parameter or session (default to "en")
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

    # Pagination parameters
    page = request.args.get("page", 1, type=int)
    per_page = 10  # Show 10 answers per page

    # Query answers sorted by created_at descending and then by id descending to break ties
    answers_query = Answer.query.filter_by(user_uuid=user.uuid).order_by(
        Answer.created_at.desc(), Answer.id.desc()
    )

    # Total the user actually has, before any tier cap.
    total_answers_all_time = answers_query.count()

    # Free tiers see only their most recent answers. Reported explicitly rather
    # than silently truncated, so a short history reads as a limit rather than as
    # lost data or a broken chart.
    history_limit = SETTINGS.TIER_HISTORY_LIMITS.get(
        user.tier, SETTINGS.TIER_HISTORY_LIMITS["free"]
    )
    history_capped = (
        history_limit is not None and total_answers_all_time > history_limit
    )
    total_answers = (
        min(total_answers_all_time, history_limit)
        if history_limit is not None
        else total_answers_all_time
    )
    total_pages = (total_answers + per_page - 1) // per_page  # Ceiling division

    # Apply pagination, never reaching past the tier's window.
    offset = (page - 1) * per_page
    page_size = per_page
    if history_limit is not None:
        page_size = max(0, min(per_page, history_limit - offset))
    answers = (
        answers_query.limit(page_size).offset(offset).all() if page_size else []
    )

    answers_dict = []
    for answer in answers:
        answer_data = answer.to_dict()
        # Add the category to each answer
        if answer.question_id and answer.question_id.startswith("custom_"):
            answer_data["category"] = "Custom"
        elif not answer_data.get("category"):
            answer_data["category"] = get_question_category(answer.question_id)
        answers_dict.append(answer_data)

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
        levels=levels_with_status,
        current_page=page,
        total_pages=total_pages,
        total_answers=total_answers,
        history_capped=history_capped,
        history_limit=history_limit,
        total_answers_all_time=total_answers_all_time,
    )


@pages_bp.route("/subscription")
def subscription():
    """Render the subscription page with plan options."""
    if "user_id" not in session:
        return redirect(url_for("pages.home"))

    # Read-only: the plan table renders the same for a visitor with no row as it
    # did for an anonymous-tier one.
    user = get_session_user()

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

    # Checkout writes the Stripe customer and subscription ids back onto the user
    # and hands uuid to Stripe as client_reference_id, so the row has to exist
    # before the first Stripe call.
    user = persist_session_user()

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

    # If the user already has a pending plan change, update it
    if user.pending_plan_change:
        try:
            # Retrieve the subscription
            subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)

            # Find the appropriate price ID
            price_id = None
            if plan == "plus":
                price_id = SETTINGS.STRIPE_PLUS_PRICE_ID
            elif plan == "pro":
                price_id = SETTINGS.STRIPE_PRO_PRICE_ID

            if price_id:
                # Update the scheduled plan change
                stripe.Subscription.modify(
                    user.stripe_subscription_id,
                    items=[
                        {
                            "id": subscription["items"]["data"][0]["id"],
                            "price": price_id,
                        }
                    ],
                    proration_behavior="none",
                    billing_cycle_anchor="unchanged",
                )

                # Update the pending plan change
                user.pending_plan_change = plan
                db.session.commit()

                return jsonify(
                    {
                        "success": True,
                        "message": "Plan change updated",
                        "redirect": url_for("pages.plan_change_scheduled"),
                    }
                )
        except Exception as e:
            current_app.logger.error(f"Error updating plan change: {str(e)}")
            return jsonify({"error": str(e)}), 500

    # Check if user is switching from Pro to Plus
    if user.tier == "pro" and plan == "plus" and user.stripe_subscription_id:
        try:
            # Schedule the downgrade to take effect at the end of the current billing period
            subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)

            # Find the Plus plan price ID
            plus_price_id = SETTINGS.STRIPE_PLUS_PRICE_ID

            # Schedule an update to switch to the Plus plan at period end
            stripe.Subscription.modify(
                user.stripe_subscription_id,
                items=[
                    {
                        "id": subscription["items"]["data"][0]["id"],
                        "price": plus_price_id,
                    }
                ],
                proration_behavior="none",  # Don't prorate, change at end of billing cycle
                billing_cycle_anchor="unchanged",  # Keep the same billing cycle
            )

            # Update user record to indicate pending plan change
            user.pending_plan_change = "plus"
            db.session.commit()

            # Return success without creating a checkout session
            return jsonify(
                {
                    "success": True,
                    "message": "Plan change scheduled",
                    "redirect": url_for("pages.plan_change_scheduled"),
                }
            )

        except Exception as e:
            current_app.logger.error(f"Error scheduling plan change: {str(e)}")
            return jsonify({"error": str(e)}), 500

    # If user is on Free tier and upgrading, or any other case, create a new checkout session
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

        # Clear any pending plan changes or cancellation status when upgrading from free
        if user.tier == "free":
            user.pending_plan_change = None
            user.is_subscription_canceled = False
            db.session.commit()

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

            # Store Stripe customer and subscription IDs
            if checkout_session.customer:
                user.stripe_customer_id = checkout_session.customer

            # Get subscription details
            if checkout_session.subscription:
                user.stripe_subscription_id = checkout_session.subscription

                # Get subscription details to store end date
                subscription = stripe.Subscription.retrieve(
                    checkout_session.subscription
                )
                if subscription:
                    # Store the current period end as the subscription end date
                    user.subscription_end_date = datetime.fromtimestamp(
                        subscription.current_period_end, UTC
                    )
                    user.is_subscription_canceled = False

                    # Clear any pending plan changes when creating a new subscription
                    user.pending_plan_change = None

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

    # No row means no subscription to change, so there is nothing to do here.
    user = load_session_user()
    if not user:
        return redirect(url_for("pages.home"))

    plan = request.form.get("plan")

    # If the user already has a pending plan change to free, just return
    if plan == "free" and user.pending_plan_change == "free":
        return redirect(url_for("pages.profile"))

    if plan == "free" and user.tier != "free":
        # Set up Stripe
        stripe.api_key = SETTINGS.STRIPE_SECRET_KEY

        # Check if the user has an active Stripe subscription
        if user.stripe_subscription_id:
            try:
                # Retrieve the subscription
                subscription = stripe.Subscription.retrieve(user.stripe_subscription_id)

                # Cancel the subscription at the end of the current period
                if subscription.status == "active":
                    stripe.Subscription.modify(
                        user.stripe_subscription_id, cancel_at_period_end=True
                    )

                    # Update the subscription end date if it's not already set
                    if subscription.current_period_end:
                        user.subscription_end_date = datetime.fromtimestamp(
                            subscription.current_period_end, UTC
                        )

                    # Mark the subscription as canceled but keep the current tier until the end date
                    user.is_subscription_canceled = True

                    # Clear any pending plan changes since we're canceling
                    user.pending_plan_change = None

                    db.session.commit()
                elif subscription.status in ["canceled", "unpaid"]:
                    # If the subscription is already canceled or unpaid, update to free tier immediately
                    user.tier = "free"
                    user.is_subscription_canceled = True
                    user.pending_plan_change = None
                    db.session.commit()
            except Exception as e:
                current_app.logger.error(f"Error canceling subscription: {str(e)}")
                # Even if there's an error with Stripe, still update the local status
                user.tier = "free"
                user.pending_plan_change = None
                db.session.commit()
        else:
            # If there's no subscription ID (shouldn't happen normally), just update the tier
            user.tier = "free"
            user.pending_plan_change = None
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

                        # Determine the plan based on price ID
                        new_plan = None
                        if price_id == SETTINGS.STRIPE_PLUS_PRICE_ID:
                            new_plan = "plus"
                        elif price_id == SETTINGS.STRIPE_PRO_PRICE_ID:
                            new_plan = "pro"

                        # If there's a pending plan change and it matches the new plan,
                        # clear the pending_plan_change field
                        if (
                            user.pending_plan_change
                            and user.pending_plan_change == new_plan
                        ):
                            user.pending_plan_change = None

                        # Update the user's tier if it's different
                        if new_plan and user.tier != new_plan:
                            user.tier = new_plan
                            # If we're updating the tier, clear any pending plan changes
                            user.pending_plan_change = None

                        # Update subscription end date
                        if "current_period_end" in subscription:
                            user.subscription_end_date = datetime.fromtimestamp(
                                subscription["current_period_end"], UTC
                            )

                        # Check if the subscription has cancel_at_period_end set
                        if subscription.get("cancel_at_period_end", False):
                            user.is_subscription_canceled = True
                        else:
                            user.is_subscription_canceled = False

                        db.session.commit()
                elif subscription["status"] in ["canceled", "unpaid"]:
                    # Only update tier to free if the subscription end date has passed
                    current_time = datetime.now(UTC)
                    if (
                        not user.subscription_end_date
                        or current_time >= user.subscription_end_date
                    ):
                        user.tier = "free"
                        user.pending_plan_change = None

                    user.is_subscription_canceled = True
                    db.session.commit()

    elif event["type"] == "customer.subscription.deleted":
        subscription = event["data"]["object"]
        user_uuid = subscription.metadata.get("user_uuid")

        if user_uuid:
            user = User.query.filter_by(uuid=user_uuid).first()
            if user:
                # Only update tier to free if the subscription end date has passed
                current_time = datetime.now(UTC)
                if (
                    not user.subscription_end_date
                    or current_time >= user.subscription_end_date
                ):
                    user.tier = "free"
                    # Clear any pending plan changes
                    user.pending_plan_change = None

                user.is_subscription_canceled = True
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
        email = data.get("email", "").strip()

        if not message or not category:
            return jsonify({"error": "Message and category are required"}), 400

        # Feedback.user_uuid is a foreign key, so a row has to exist to point at.
        # Creating one here is deliberate: writing feedback is a considered human
        # action, the volume is negligible next to page views, and a user_uuid
        # that joins to nothing would make the record useless.
        user = persist_session_user()

        feedback = Feedback(
            user_uuid=user.uuid,
            message=message,
            category=category,
            email=email if email else None,
        )

        db.session.add(feedback)
        db.session.commit()

        # Send email notification to admin
        try:
            user_info = f"From user: {user.username} (ID: {user.uuid})"

            contact_info = (
                f"Contact email: {email}" if email else "No contact email provided"
            )

            msg = Message(
                subject=f"New Feedback: {category}",
                sender=SETTINGS.MAIL_DEFAULT_SENDER,
                recipients=[SETTINGS.MAIL_USERNAME],
                body=f"""
New feedback has been submitted:

Category: {category}
{user_info}
{contact_info}

Message:
{message}

Timestamp: {datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")}
                """,
            )
            mail.send(msg)
        except Exception as e:
            # Log the error but don't fail the feedback submission
            logging.error(f"Failed to send feedback notification email: {str(e)}")

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
    is_first_time_visit = data.get("isFirstTimeVisit", False)

    if language in ["en", "de"]:
        session["language"] = language
        # Track if this is a first-time visit for the redirected language
        # Only set is_first_time_visit in the session if it's explicitly True
        if is_first_time_visit is True:
            session["is_first_time_visit"] = True
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


def maintenance_key_ok():
    """Authorise a Cloud Scheduler call against the app's SECRET_KEY.

    There is no separate API key. The value arrives in the query string, which is
    how the first of these endpoints was written and therefore how the existing
    scheduler job is configured — see the note in DEPLOY.md about moving it to a
    header, which would need both endpoints and both jobs changed together.
    """
    api_key = request.args.get("api_key")
    if not api_key:
        return False
    # Encoded, because compare_digest rejects str containing non-ASCII, and the
    # secret is whatever was put in Secret Manager.
    return hmac.compare_digest(
        api_key.encode(), current_app.config["SECRET_KEY"].encode()
    )


@pages_bp.route("/check-subscription-expirations", methods=["GET"])
def check_subscription_expirations():
    """Check for expired subscriptions and update user tiers."""
    if not maintenance_key_ok():
        return jsonify({"error": "Unauthorized"}), 401

    # Set up Stripe
    stripe.api_key = SETTINGS.STRIPE_SECRET_KEY

    # Get current time
    current_time = datetime.now(UTC)

    # Find users with expired subscriptions who haven't been moved to free tier yet
    expired_subscriptions = User.query.filter(
        User.is_subscription_canceled,
        User.subscription_end_date <= current_time,
        User.tier.in_(["plus", "pro"]),
    ).all()

    updated_count = 0
    for user in expired_subscriptions:
        user.tier = "free"
        user.pending_plan_change = None
        updated_count += 1

    # Find users with pending plan changes whose subscription period has ended
    pending_plan_changes = User.query.filter(
        User.pending_plan_change.isnot(None),
        User.subscription_end_date <= current_time,
    ).all()

    plan_change_count = 0
    for user in pending_plan_changes:
        # Update the user's tier to the pending plan
        user.tier = user.pending_plan_change
        user.pending_plan_change = None
        plan_change_count += 1

    if updated_count > 0 or plan_change_count > 0:
        db.session.commit()

    return jsonify(
        {
            "success": True,
            "message": f"Checked subscription expirations. Updated {updated_count} users to free tier. Applied {plan_change_count} pending plan changes.",
        }
    )


@pages_bp.route("/prune-visits", methods=["GET"])
def prune_visits():
    """Delete visit rows older than the retention window.

    The visit table is append-only and nothing in the app reads it, so without a
    retention policy it grows forever against a 500 MB Supabase cap.

    Note that deleting rows does not shrink the database on disk — Postgres marks
    the space reusable, it does not return it to the filesystem. That is fine for
    an ongoing trim, where the freed space is immediately reused by new rows, but
    it means this endpoint alone will not recover the size of a backlog. See the
    VACUUM FULL step in DEPLOY.md for that.
    """
    if not maintenance_key_ok():
        return jsonify({"error": "Unauthorized"}), 401

    # Naive UTC, because created_at is `timestamp without time zone` holding UTC
    # wall time. Passing an aware datetime would leave the comparison at the
    # mercy of the server's TimeZone setting.
    cutoff = (
        datetime.now(UTC) - timedelta(days=SETTINGS.VISIT_RETENTION_DAYS)
    ).replace(tzinfo=None)

    deleted = (
        db.session.query(Visit)
        .filter(Visit.created_at < cutoff)
        .delete(synchronize_session=False)
    )
    db.session.commit()

    logging.info(f"Pruned {deleted} visits older than {cutoff.isoformat()}")

    return jsonify(
        {
            "success": True,
            "deleted": deleted,
            "cutoff": cutoff.isoformat(),
            "retention_days": SETTINGS.VISIT_RETENTION_DAYS,
        }
    )


@pages_bp.route("/plan-change-scheduled")
def plan_change_scheduled():
    """Show confirmation page for scheduled plan changes."""
    if "user_id" not in session:
        return redirect(url_for("pages.home"))

    # Only a user with a row can have a pending plan change.
    user = load_session_user()
    if not user:
        return redirect(url_for("pages.home"))

    # If no pending plan change, redirect to subscription page
    if not user.pending_plan_change:
        return redirect(url_for("pages.subscription"))

    return render_template(
        "plan_change_scheduled.html",
        user=user,
        current_plan=user.tier.title(),
        new_plan=user.pending_plan_change.title(),
        subscription_end_date=user.subscription_end_date,
        current_year=datetime.now().year,
    )


@pages_bp.route("/login")
def login_page():
    """
    Redirect to home page with a query parameter to open the login modal.
    This is used for direct links to the login page.
    """
    # If user is already authenticated, redirect to home page without show_login parameter
    if current_user.is_authenticated:
        return redirect(url_for("pages.home"))

    # Otherwise, redirect to home page with show_login parameter
    return redirect(url_for("pages.home") + "?show_login=true")
