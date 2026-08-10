"""Anonymous visitors must not reach the database until they do something.

These guard the invariant behind the Aug 2026 identity change: browsing writes
nothing, and a `users` row appears at the first action that needs one. Regressing
it is easy and quiet — one `User.query...first()` replaced by a create, and the
table starts filling with bot rows again.
"""

from datetime import UTC, datetime, timedelta
from unittest import mock

from extensions import db
from models import Answer, User, Visit

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


def test_browsing_creates_no_user_row(client):
    for path in ("/", "/profile", "/subscription", "/how_it_works"):
        assert client.get(path).status_code == 200, path

    assert User.query.count() == 0


def test_every_request_from_a_fresh_client_creates_no_user_row(app):
    # A client that never returns the session cookie is what a crawler looks
    # like, and what used to produce one row per request.
    for _ in range(5):
        assert app.test_client().get("/").status_code == 200

    assert User.query.count() == 0


def test_no_visit_is_logged_for_a_client_that_returns_no_cookie(app):
    for _ in range(5):
        app.test_client().get("/")

    assert Visit.query.count() == 0


def test_one_visit_is_logged_per_day_once_the_cookie_comes_back(client):
    client.get("/")  # mints the session, logs nothing
    client.get("/")  # cookie returned, so this is a real visitor
    client.get("/")  # same day, already counted

    assert Visit.query.count() == 1


def test_anonymous_visit_is_not_linked_to_a_user(client):
    client.get("/")
    client.get("/")

    assert Visit.query.one().user_uuid is None


def test_submitting_an_answer_creates_exactly_one_user(client):
    client.get("/")

    response = client.post("/submit_answer", json=ANSWER)

    assert response.status_code == 200
    user = User.query.one()
    assert user.tier == "anonymous"
    assert Answer.query.filter_by(user_uuid=user.uuid).count() == 1


def test_a_second_answer_reuses_the_same_user(client):
    client.get("/")
    client.post("/submit_answer", json=ANSWER)
    client.post("/submit_answer", json={**ANSWER, "claim": "A different claim."})

    assert User.query.count() == 1
    assert Answer.query.count() == 2


def test_a_rejected_submission_creates_no_user(client):
    client.get("/")

    response = client.post("/submit_answer", json={**ANSWER, "argument": ""})

    assert response.status_code == 400
    assert User.query.count() == 0


def test_voice_limits_are_reported_without_creating_a_user(client):
    client.get("/")

    response = client.get("/check_voice_limits")

    assert response.status_code == 200
    assert response.get_json()["limit_reached"] is False
    assert User.query.count() == 0


def test_update_session_reports_an_empty_user_without_creating_one(client):
    client.get("/")

    response = client.post("/update_session", json={})

    assert response.status_code == 200
    assert response.get_json()["xp"] == 0
    assert User.query.count() == 0


def test_feedback_persists_the_user_it_points_at(client):
    client.get("/")

    with mock.patch("routes.pages.mail.send"):
        response = client.post(
            "/submit_feedback", json={"message": "Nice app", "category": "general"}
        )

    assert response.status_code == 200
    # feedback.user_uuid is a foreign key, so the row has to be there.
    assert User.query.count() == 1


def test_challenge_response_rejects_another_visitors_answer(app, client):
    client.get("/")
    answer_id = client.post("/submit_answer", json=ANSWER).get_json()["answer_id"]

    attacker = app.test_client()
    attacker.get("/")
    response = attacker.post(
        "/submit_challenge_response",
        json={"answer_id": answer_id, "challenge_response": "Let me try again."},
    )

    assert response.status_code == 404
    assert Answer.query.one().challenge_response is None


def test_fetching_questions_creates_no_user(client):
    client.get("/")
    assert client.get("/get_question").status_code == 200
    # The second call takes the random path, which looks up the visitor's
    # previous answers by session user_id.
    assert client.get("/get_question").status_code == 200

    assert User.query.count() == 0


def test_signup_without_prior_activity_creates_one_user(client):
    client.get("/")

    response = client.post(
        "/signup",
        json={
            "email": "new@example.com",
            "password": "correct horse battery staple",
            "username": "newcomer",
        },
    )

    assert response.status_code == 200
    assert User.query.one().email == "new@example.com"


def test_signup_carries_over_answers_submitted_anonymously(client):
    client.get("/")
    client.post("/submit_answer", json=ANSWER)

    response = client.post(
        "/signup",
        json={
            "email": "convert@example.com",
            "password": "correct horse battery staple",
            "username": "convert",
        },
    )

    assert response.status_code == 200
    # The anonymous row is merged into the account, not left behind.
    user = User.query.one()
    assert user.email == "convert@example.com"
    assert Answer.query.one().user_uuid == user.uuid


def test_visit_is_linked_once_the_visitor_is_authenticated(client):
    client.get("/")
    client.post(
        "/signup",
        json={
            "email": "linked@example.com",
            "password": "correct horse battery staple",
            "username": "linked",
        },
    )

    # Visits are logged once per day, and today's was already logged during the
    # signup request, while the visitor was still anonymous. Clearing the marker
    # stands in for their next visit on another day.
    with client.session_transaction() as flask_session:
        flask_session.pop("last_visit_date", None)
    client.get("/")

    linked = Visit.query.filter(Visit.user_uuid.isnot(None)).one()
    assert linked.user_uuid == User.query.one().uuid


def test_created_at_is_the_insert_time_not_the_import_time(app):
    # default=datetime.now(UTC) evaluates once at import, so every row written by
    # a worker shared one timestamp. Retention depends on this being per-row.
    first = Visit(ip_address="198.51.100.1")
    db.session.add(first)
    db.session.commit()
    second = Visit(ip_address="198.51.100.2")
    db.session.add(second)
    db.session.commit()

    assert first.created_at != second.created_at


def test_prune_visits_deletes_only_beyond_the_retention_window(app, client):
    now = datetime.now(UTC).replace(tzinfo=None)
    db.session.add_all(
        [
            Visit(ip_address="198.51.100.1", created_at=now - timedelta(days=200)),
            Visit(ip_address="198.51.100.2", created_at=now - timedelta(days=1)),
        ]
    )
    db.session.commit()

    response = client.get(f"/prune-visits?api_key={app.config['SECRET_KEY']}")

    assert response.get_json()["deleted"] == 1
    assert Visit.query.one().ip_address == "198.51.100.2"


def test_prune_visits_requires_the_maintenance_key(client):
    assert client.get("/prune-visits").status_code == 401
    assert client.get("/prune-visits?api_key=wrong").status_code == 401
