"""The deep analysis gate and its monthly counter.

Deep analysis is the only endpoint that spends real money per call — ~16x a
normal evaluation, see DEEP_ANALYSIS_MODEL in config.py — so the gate and the
counter are the cost ceiling, not a nicety. The Vertex call itself is stubbed
here; the model's output is checked by deploying, because that is the only place
it can be.
"""

from datetime import UTC, datetime, timedelta
from unittest import mock

from config import get_settings
from extensions import db
from models import Answer, User

SETTINGS = get_settings()

ANSWER = {
    "question_id": "experiences",
    "question_text": "Do experiences make you happier than possessions?",
    "claim": "Experiences beat possessions.",
    "argument": (
        "Possessions lose their novelty because we adapt to them, while "
        "experiences keep paying out as memories that we revisit and retell."
    ),
    "counterargument": "Some possessions do enable repeated experiences.",
}

ANALYSIS = {
    "verdict": "Establishes less than it claims.",
    "reconstruction": [
        {"step": "Adaptation weakens possessions.", "assessment": "Holds."}
    ],
    "unstated_assumptions": [
        {
            "assumption": "Memory is reliable.",
            "why_it_matters": "The payout depends on it.",
        }
    ],
    "counterarguments": [
        {
            "objection": "Recalled experiences also fade.",
            "why_it_bites": "It attacks the asymmetry you rely on.",
            "what_would_answer_it": "Show the decay rates differ.",
        }
    ],
    "rebuild": ["Argue for the memory premise instead of assuming it."],
}


def _answer_for(client, tier=None):
    """Submit an answer, optionally promoting the resulting user to a paid tier."""
    client.get("/")
    answer_id = client.post("/submit_answer", json=ANSWER).get_json()["answer_id"]
    if tier:
        user = User.query.one()
        user.tier = tier
        db.session.commit()
    return answer_id


def _request(client, answer_id):
    with mock.patch(
        "routes.deep_analysis.run_deep_analysis", return_value=ANALYSIS
    ) as run:
        response = client.post("/deep_analysis", json={"answer_id": answer_id})
    return response, run


def test_anonymous_gets_402(client):
    answer_id = _answer_for(client)

    response, run = _request(client, answer_id)

    assert response.status_code == 402
    assert response.get_json()["status"] == "upgrade_required"
    # The gate has to come before the spend, not after it.
    run.assert_not_called()


def test_free_gets_402(client):
    answer_id = _answer_for(client, tier="free")

    response, run = _request(client, answer_id)

    assert response.status_code == 402
    assert response.get_json()["status"] == "upgrade_required"
    run.assert_not_called()


def test_plus_gets_a_result_and_it_is_stored(client):
    answer_id = _answer_for(client, tier="plus")

    response, run = _request(client, answer_id)

    assert response.status_code == 200
    assert response.get_json()["analysis"] == ANALYSIS
    run.assert_called_once()
    answer = Answer.query.one()
    assert answer.deep_analysis == ANALYSIS
    assert answer.deep_analysis_created_at is not None


def test_pro_gets_a_result(client):
    answer_id = _answer_for(client, tier="pro")

    response, _ = _request(client, answer_id)

    assert response.status_code == 200


def test_the_counter_increments(client):
    answer_id = _answer_for(client, tier="plus")

    _request(client, answer_id)

    user = User.query.one()
    assert user.monthly_deep_analysis_count == 1
    assert user.last_monthly_deep_analysis_reset is not None


def test_a_second_request_for_the_same_answer_is_free(client):
    answer_id = _answer_for(client, tier="plus")
    _request(client, answer_id)

    response, run = _request(client, answer_id)

    assert response.status_code == 200
    assert response.get_json()["cached"] is True
    # Neither a second model call nor a second charge against the allowance.
    run.assert_not_called()
    assert User.query.one().monthly_deep_analysis_count == 1


def test_it_blocks_at_the_limit(client):
    answer_id = _answer_for(client, tier="plus")
    user = User.query.one()
    limit = SETTINGS.TIER_MONTHLY_DEEP_ANALYSIS_LIMITS["plus"]
    user.monthly_deep_analysis_count = limit
    user.last_monthly_deep_analysis_reset = datetime.now(UTC)
    db.session.commit()

    response, run = _request(client, answer_id)

    assert response.status_code == 429
    assert response.get_json()["status"] == "limit_reached"
    run.assert_not_called()


def test_the_counter_resets_in_a_new_month(client):
    answer_id = _answer_for(client, tier="plus")
    user = User.query.one()
    user.monthly_deep_analysis_count = SETTINGS.TIER_MONTHLY_DEEP_ANALYSIS_LIMITS[
        "plus"
    ]
    # Any reset stamp before the 1st of this month is a spent *previous* month.
    now = datetime.now(UTC)
    user.last_monthly_deep_analysis_reset = datetime(
        now.year, now.month, 1, tzinfo=UTC
    ) - timedelta(days=1)
    db.session.commit()

    response, run = _request(client, answer_id)

    assert response.status_code == 200
    run.assert_called_once()
    # Reset to zero, then charged for this call.
    assert User.query.one().monthly_deep_analysis_count == 1


def test_a_failed_call_costs_no_allowance(client):
    answer_id = _answer_for(client, tier="plus")

    with mock.patch(
        "routes.deep_analysis.run_deep_analysis", side_effect=RuntimeError("vertex 503")
    ):
        response = client.post("/deep_analysis", json={"answer_id": answer_id})

    assert response.status_code == 502
    user = User.query.one()
    assert not user.monthly_deep_analysis_count
    assert Answer.query.one().deep_analysis is None


def test_another_visitors_answer_is_not_analysable(app, client):
    answer_id = _answer_for(client, tier="plus")
    owner_uuid = User.query.one().uuid

    # The attacker is on the highest tier, so only ownership can stop them.
    attacker = app.test_client()
    attacker.get("/")
    attacker.post("/submit_answer", json={**ANSWER, "claim": "Something else."})
    attacker_user = User.query.filter(User.uuid != owner_uuid).one()
    attacker_user.tier = "pro"
    db.session.commit()

    with mock.patch(
        "routes.deep_analysis.run_deep_analysis", return_value=ANALYSIS
    ) as run:
        response = attacker.post("/deep_analysis", json={"answer_id": answer_id})

    # 404, not 403: this must not confirm that someone else's answer id exists.
    assert response.status_code == 404
    run.assert_not_called()


def test_the_button_is_rendered_only_for_paid_tiers(client):
    client.get("/")
    assert b'id="deepAnalysisBtn"' not in client.get("/").data

    client.post(
        "/signup",
        json={
            "email": "paid@example.com",
            "password": "correct horse battery staple",
            "username": "paid",
        },
    )
    assert b'id="deepAnalysisBtn"' not in client.get("/").data

    user = User.query.one()
    user.tier = "plus"
    db.session.commit()
    # A visible button that 402s is worse than no button, so this is the gate.
    assert b'id="deepAnalysisBtn"' in client.get("/").data
