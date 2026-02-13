"""
Tests for the Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from urllib.parse import quote

from src.app import app, activities


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture(autouse=True)
def reset_activities():
    """Reset activities to a known state before each test."""
    # Store original participants
    original_participants = {
        name: list(details["participants"])
        for name, details in activities.items()
    }
    yield
    # Restore original participants after test
    for name, participants in original_participants.items():
        activities[name]["participants"] = participants


class TestRootEndpoint:
    """Tests for the root endpoint."""

    def test_root_redirects_to_static(self, client):
        """Test that root redirects to the static index page."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestGetActivities:
    """Tests for the GET /activities endpoint."""

    def test_get_activities_returns_all_activities(self, client):
        """Test that all activities are returned."""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        assert "Soccer Team" in data
        assert "Basketball Club" in data
        assert "Drama Club" in data

    def test_activity_has_required_fields(self, client):
        """Test that each activity has all required fields."""
        response = client.get("/activities")
        assert response.status_code == 200
        data = response.json()
        for name, activity in data.items():
            assert "description" in activity
            assert "schedule" in activity
            assert "max_participants" in activity
            assert "participants" in activity


class TestSignup:
    """Tests for the POST /activities/{activity_name}/signup endpoint."""

    def test_signup_success(self, client):
        """Test successful signup for an activity."""
        response = client.post(
            f"/activities/{quote('Soccer Team')}/signup?email=newstudent@mergington.edu"
        )
        assert response.status_code == 200
        assert "newstudent@mergington.edu" in response.json()["message"]

    def test_signup_adds_participant(self, client):
        """Test that signup actually adds the participant to the activity."""
        email = "testuser@mergington.edu"
        client.post(f"/activities/{quote('Chess Club')}/signup?email={email}")
        
        response = client.get("/activities")
        assert email in response.json()["Chess Club"]["participants"]

    def test_signup_activity_not_found(self, client):
        """Test signup for non-existent activity returns 404."""
        response = client.post(
            f"/activities/{quote('Nonexistent Activity')}/signup?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_signup_duplicate_registration(self, client):
        """Test that duplicate registration is rejected."""
        email = "duplicate@mergington.edu"
        # First signup should succeed
        response1 = client.post(f"/activities/{quote('Art Studio')}/signup?email={email}")
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(f"/activities/{quote('Art Studio')}/signup?email={email}")
        assert response2.status_code == 400
        assert "already signed up" in response2.json()["detail"]

    def test_signup_invalid_email(self, client):
        """Test that invalid email format is rejected."""
        response = client.post(
            f"/activities/{quote('Soccer Team')}/signup?email=invalid-email"
        )
        assert response.status_code == 400
        assert "Invalid email format" in response.json()["detail"]

    def test_signup_empty_email(self, client):
        """Test that empty email is rejected."""
        response = client.post(
            f"/activities/{quote('Soccer Team')}/signup?email="
        )
        assert response.status_code == 400
        assert "cannot be empty" in response.json()["detail"]

    def test_signup_email_normalization(self, client):
        """Test that email is normalized (whitespace trimmed)."""
        email = "  test@mergington.edu  "
        response = client.post(f"/activities/{quote('Chess Club')}/signup?email={email}")
        assert response.status_code == 200
        
        # Check that the normalized email (without spaces) is in participants
        activities_response = client.get("/activities")
        assert "test@mergington.edu" in activities_response.json()["Chess Club"]["participants"]


class TestUnregister:
    """Tests for the DELETE /activities/{activity_name}/unregister endpoint."""

    def test_unregister_success(self, client):
        """Test successful unregistration from an activity."""
        # First register
        email = "tounregister@mergington.edu"
        client.post(f"/activities/{quote('Math Olympiad')}/signup?email={email}")
        
        # Then unregister
        response = client.delete(
            f"/activities/{quote('Math Olympiad')}/unregister?email={email}"
        )
        assert response.status_code == 200
        assert email in response.json()["message"]

    def test_unregister_removes_participant(self, client):
        """Test that unregister actually removes the participant."""
        email = "removetest@mergington.edu"
        client.post(f"/activities/{quote('Debate Society')}/signup?email={email}")
        client.delete(f"/activities/{quote('Debate Society')}/unregister?email={email}")
        
        response = client.get("/activities")
        assert email not in response.json()["Debate Society"]["participants"]

    def test_unregister_activity_not_found(self, client):
        """Test unregister from non-existent activity returns 404."""
        response = client.delete(
            f"/activities/{quote('Nonexistent Activity')}/unregister?email=test@mergington.edu"
        )
        assert response.status_code == 404
        assert "Activity not found" in response.json()["detail"]

    def test_unregister_not_registered(self, client):
        """Test unregister when not registered returns 400."""
        response = client.delete(
            f"/activities/{quote('Programming Class')}/unregister?email=notregistered@mergington.edu"
        )
        assert response.status_code == 400
        assert "not registered" in response.json()["detail"]
