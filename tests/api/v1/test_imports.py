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


def test_import_estimate_analytics_success(client, tmp_path):
    headers = {"Authorization": f"Bearer {fake_jwt()}"}
    # Testa .pdf
    file_content = b"fake pdf content"
    file_path = tmp_path / "estimate.pdf"
    file_path.write_bytes(file_content)
    with open(file_path, "rb") as f:
        response = client.post(
            "/v1/imports/estimate_analytics",
            files={"file": ("estimate.pdf", f, "application/pdf")},
            headers=headers
        )
    assert response.status_code == 202
    data = response.json()
    assert "import_id" in data
    assert data["message"] == "Documento recebido e enfileirado para análise de estimativas."

    # Testa .docx
    file_path_docx = tmp_path / "estimate.docx"
    file_path_docx.write_bytes(file_content)
    with open(file_path_docx, "rb") as f:
        response = client.post(
            "/v1/imports/estimate_analytics",
            files={"file": ("estimate.docx", f, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
            headers=headers
        )
    assert response.status_code == 202
    data = response.json()
    assert "import_id" in data
    assert data["message"] == "Documento recebido e enfileirado para análise de estimativas."

    # Testa .xlsx
    file_path_xlsx = tmp_path / "estimate.xlsx"
    file_path_xlsx.write_bytes(file_content)
    with open(file_path_xlsx, "rb") as f:
        response = client.post(
            "/v1/imports/estimate_analytics",
            files={"file": ("estimate.xlsx", f, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
            headers=headers
        )
    assert response.status_code == 202
    data = response.json()
    assert "import_id" in data
    assert data["message"] == "Documento recebido e enfileirado para análise de estimativas."

    # Testa .csv
    file_path_csv = tmp_path / "estimate.csv"
    file_path_csv.write_bytes(file_content)
    with open(file_path_csv, "rb") as f:
        response = client.post(
            "/v1/imports/estimate_analytics",
            files={"file": ("estimate.csv", f, "text/csv")},
            headers=headers
        )
    assert response.status_code == 202
    data = response.json()
    assert "import_id" in data
    assert data["message"] == "Documento recebido e enfileirado para análise de estimativas."

def test_import_estimate_analytics_invalid_extension(client, tmp_path):
    headers = {"Authorization": f"Bearer {fake_jwt()}"}
    file_content = b"not allowed"
    file_path = tmp_path / "estimate.txt"
    file_path.write_bytes(file_content)
    with open(file_path, "rb") as f:
        response = client.post(
            "/v1/imports/estimate_analytics",
            files={"file": ("estimate.txt", f, "text/plain")},
            headers=headers
        )
    assert response.status_code == 400
    data = response.json()
    assert data["detail"] == "Arquivo deve ser PDF, DOCX, XLS, XLSX ou CSV"
