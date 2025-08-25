import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def fake_jwt():
    # JWT simulado para testes (ajuste conforme necessário)
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJ0ZXN0LXRlbmFudCIsInN1YiI6InRlc3QtdXNlciJ9.DQw1Qw2Qw3Qw4Qw5Qw6Qw7Qw8Qw9Qw0Qw1Qw2Qw3Qw4"

def test_list_locations_success(client):
    headers = {"Authorization": f"Bearer {fake_jwt()}"}
    response = client.get("/v1/locations/", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "locations" in data
    assert isinstance(data["locations"], list)
    assert len(data["locations"]) > 0
    assert "id" in data["locations"][0]
    assert "name" in data["locations"][0]
