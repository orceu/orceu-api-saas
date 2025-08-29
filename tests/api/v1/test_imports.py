import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    return TestClient(app)

def fake_jwt():
    return "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0ZW5hbnRfaWQiOiJ0ZXN0LXRlbmFudCIsInN1YiI6InRlc3QtdXNlciJ9.DQw1Qw2Qw3Qw4Qw5Qw6Qw7Qw8Qw9Qw0Qw1Qw2Qw3Qw4"

def test_import_excel_file_success(client, tmp_path):
    headers = {"Authorization": f"Bearer {fake_jwt()}"}
    # Testa .xlsx
    file_content = b"fake excel content"
    file_path = tmp_path / "import.xlsx"
    file_path.write_bytes(file_content)
    with open(file_path, "rb") as f:
        response = client.post(
            "/v1/imports/excel",
            files={"file": ("import.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers
        )
    assert response.status_code == 202
    data = response.json()
    assert "import_id" in data
    assert data["message"] == "Arquivo Excel recebido e enfileirado para importação."

    # Testa .xls
    file_path_xls = tmp_path / "import.xls"
    file_path_xls.write_bytes(file_content)
    with open(file_path_xls, "rb") as f:
        response = client.post(
            "/v1/imports/excel",
            files={"file": ("import.xls", f, "application/vnd.ms-excel")},
            headers=headers
        )
    assert response.status_code == 202
    data = response.json()
    assert "import_id" in data
    assert data["message"] == "Arquivo Excel recebido e enfileirado para importação."

def test_import_excel_file_invalid_extension(client, tmp_path):
    headers = {"Authorization": f"Bearer {fake_jwt()}"}
    file_content = b"not excel"
    file_path = tmp_path / "import.txt"
    file_path.write_bytes(file_content)
    with open(file_path, "rb") as f:
        response = client.post(
            "/v1/imports/excel",
            files={"file": ("import.txt", f, "text/plain")},
            headers=headers
        )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Arquivo deve ser .xls ou .xlsx"
