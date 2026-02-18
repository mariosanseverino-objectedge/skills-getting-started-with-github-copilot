"""Tests for the Mergington High School API."""

import pytest
from fastapi.testclient import TestClient

from src.app import app, activities


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to their original state before each test."""
    import copy
    original = copy.deepcopy(activities)
    yield
    activities.clear()
    activities.update(original)


@pytest.fixture
def client():
    return TestClient(app)


# ---------- GET / ----------

class TestRoot:
    def test_root_redirects_to_index(self, client):
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


# ---------- GET /activities ----------

class TestGetActivities:
    def test_get_activities_returns_all(self, client):
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)
        assert "Soccer Club" in data
        assert "Basketball Club" in data
        assert "Chess Club" in data

    def test_activity_has_expected_fields(self, client):
        response = client.get("/activities")
        data = response.json()
        for name, info in data.items():
            assert "description" in info
            assert "schedule" in info
            assert "max_participants" in info
            assert "participants" in info


# ---------- POST /activities/{name}/signup ----------

class TestSignup:
    def test_signup_success(self, client):
        response = client.post(
            "/activities/Soccer Club/signup",
            params={"email": "newstudent@mergington.edu"},
        )
        assert response.status_code == 200
        assert "newstudent@mergington.edu" in response.json()["message"]

    def test_signup_adds_participant(self, client):
        client.post(
            "/activities/Chess Club/signup",
            params={"email": "newplayer@mergington.edu"},
        )
        data = client.get("/activities").json()
        assert "newplayer@mergington.edu" in data["Chess Club"]["participants"]

    def test_signup_activity_not_found(self, client):
        response = client.post(
            "/activities/Nonexistent Club/signup",
            params={"email": "test@mergington.edu"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_signup_duplicate_email(self, client):
        response = client.post(
            "/activities/Soccer Club/signup",
            params={"email": "liam@mergington.edu"},
        )
        assert response.status_code == 400
        assert "already signed up" in response.json()["detail"]

    def test_signup_activity_full(self, client):
        """Signing up should fail when the activity has reached max_participants."""
        # Fill Math Olympiad Prep (max 12, starts with 2) with 10 more students
        for i in range(10):
            resp = client.post(
                "/activities/Math Olympiad Prep/signup",
                params={"email": f"student{i}@mergington.edu"},
            )
            assert resp.status_code == 200

        # The 13th signup should be rejected
        response = client.post(
            "/activities/Math Olympiad Prep/signup",
            params={"email": "onemore@mergington.edu"},
        )
        assert response.status_code == 400
        assert "maximum" in response.json()["detail"]


# ---------- DELETE /activities/{name}/unregister ----------

class TestUnregister:
    def test_unregister_success(self, client):
        response = client.delete(
            "/activities/Soccer Club/unregister",
            params={"email": "liam@mergington.edu"},
        )
        assert response.status_code == 200
        assert "Unregistered" in response.json()["message"]

    def test_unregister_removes_participant(self, client):
        client.delete(
            "/activities/Soccer Club/unregister",
            params={"email": "liam@mergington.edu"},
        )
        data = client.get("/activities").json()
        assert "liam@mergington.edu" not in data["Soccer Club"]["participants"]

    def test_unregister_activity_not_found(self, client):
        response = client.delete(
            "/activities/Nonexistent Club/unregister",
            params={"email": "test@mergington.edu"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Activity not found"

    def test_unregister_email_not_signed_up(self, client):
        response = client.delete(
            "/activities/Soccer Club/unregister",
            params={"email": "unknown@mergington.edu"},
        )
        assert response.status_code == 400
        assert "not signed up" in response.json()["detail"]
