"""
Test suite for Mergington High School Activities API
"""

import pytest
from fastapi.testclient import TestClient
from src.app import app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app"""
    return TestClient(app)


@pytest.fixture
def reset_activities():
    """Reset activities to known state before each test"""
    from src.app import activities
    original_participants = {}
    for activity_name, activity_data in activities.items():
        original_participants[activity_name] = activity_data["participants"].copy()
    
    yield
    
    # Reset after test
    for activity_name, activity_data in activities.items():
        activity_data["participants"] = original_participants[activity_name]


class TestGetActivities:
    """Tests for GET /activities endpoint"""
    
    def test_get_activities_returns_all_activities(self, client):
        """Test that GET /activities returns all available activities"""
        response = client.get("/activities")
        assert response.status_code == 200
        activities = response.json()
        assert isinstance(activities, dict)
        assert len(activities) > 0
        assert "Basketball Team" in activities
    
    def test_activities_have_required_fields(self, client):
        """Test that each activity has required fields"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)


class TestSignupForActivity:
    """Tests for POST /activities/{activity_name}/signup endpoint"""
    
    def test_signup_successful(self, client, reset_activities):
        """Test successful signup for an activity"""
        response = client.post(
            "/activities/Basketball Team/signup",
            params={"email": "newstudent@mergington.edu"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "newstudent@mergington.edu" in data["message"]
    
    def test_signup_adds_participant(self, client, reset_activities):
        """Test that signup actually adds the participant"""
        email = "newstudent@mergington.edu"
        client.post(
            "/activities/Basketball Team/signup",
            params={"email": email}
        )
        
        # Verify participant was added
        response = client.get("/activities")
        activities = response.json()
        assert email in activities["Basketball Team"]["participants"]
    
    def test_signup_duplicate_email_rejected(self, client, reset_activities):
        """Test that duplicate signup is rejected"""
        email = "duplicate@mergington.edu"
        
        # First signup succeeds
        response1 = client.post(
            "/activities/Basketball Team/signup",
            params={"email": email}
        )
        assert response1.status_code == 200
        
        # Second signup should fail
        response2 = client.post(
            "/activities/Basketball Team/signup",
            params={"email": email}
        )
        assert response2.status_code == 400
        data = response2.json()
        assert "already signed up" in data["detail"]
    
    def test_signup_invalid_activity(self, client):
        """Test signup for non-existent activity"""
        response = client.post(
            "/activities/Nonexistent Activity/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]
    
    def test_signup_multiple_different_students(self, client, reset_activities):
        """Test that multiple students can sign up for the same activity"""
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        for email in emails:
            response = client.post(
                "/activities/Drama Club/signup",
                params={"email": email}
            )
            assert response.status_code == 200
        
        # Verify all were added
        response = client.get("/activities")
        activities = response.json()
        for email in emails:
            assert email in activities["Drama Club"]["participants"]


class TestUnregisterFromActivity:
    """Tests for DELETE /activities/{activity_name}/signup endpoint"""
    
    def test_unregister_successful(self, client, reset_activities):
        """Test successful unregistration from an activity"""
        # First, get an existing participant
        response = client.get("/activities")
        activities = response.json()
        basketball_participants = activities["Basketball Team"]["participants"]
        existing_participant = basketball_participants[0]
        
        # Unregister them
        response = client.delete(
            "/activities/Basketball Team/signup",
            params={"email": existing_participant}
        )
        assert response.status_code == 200
        data = response.json()
        assert "Unregistered" in data["message"]
    
    def test_unregister_removes_participant(self, client, reset_activities):
        """Test that unregister actually removes the participant"""
        email = "temp@mergington.edu"
        
        # Sign up first
        client.post(
            "/activities/Tennis Club/signup",
            params={"email": email}
        )
        
        # Verify signup worked
        response = client.get("/activities")
        activities = response.json()
        assert email in activities["Tennis Club"]["participants"]
        
        # Unregister
        client.delete(
            "/activities/Tennis Club/signup",
            params={"email": email}
        )
        
        # Verify removed
        response = client.get("/activities")
        activities = response.json()
        assert email not in activities["Tennis Club"]["participants"]
    
    def test_unregister_not_registered_student(self, client):
        """Test unregistering a student who isn't registered"""
        response = client.delete(
            "/activities/Art Studio/signup",
            params={"email": "notregistered@mergington.edu"}
        )
        assert response.status_code == 400
        data = response.json()
        assert "not registered" in data["detail"]
    
    def test_unregister_invalid_activity(self, client):
        """Test unregistering from non-existent activity"""
        response = client.delete(
            "/activities/Nonexistent Activity/signup",
            params={"email": "test@mergington.edu"}
        )
        assert response.status_code == 404
        data = response.json()
        assert "not found" in data["detail"]


class TestActivityConstraints:
    """Tests for activity constraints and business logic"""
    
    def test_activity_max_participants_field_exists(self, client):
        """Test that activities have max_participants defined"""
        response = client.get("/activities")
        activities = response.json()
        
        for activity_name, activity_data in activities.items():
            assert activity_data["max_participants"] > 0
            assert len(activity_data["participants"]) <= activity_data["max_participants"]
    
    def test_participant_list_consistency(self, client, reset_activities):
        """Test that participant lists remain consistent through signup/unregister"""
        email = "consistent@mergington.edu"
        
        # Sign up
        client.post(
            "/activities/Debate Team/signup",
            params={"email": email}
        )
        
        response1 = client.get("/activities")
        count1 = len(response1.json()["Debate Team"]["participants"])
        
        # Unregister
        client.delete(
            "/activities/Debate Team/signup",
            params={"email": email}
        )
        
        response2 = client.get("/activities")
        count2 = len(response2.json()["Debate Team"]["participants"])
        
        assert count2 == count1 - 1
