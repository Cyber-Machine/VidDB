from fastapi.testclient import TestClient

from apps.api.main import app


def test_dashboard_ui_renders_api_console() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "VideoDB Console" in response.text
    assert "POST /search" in response.text
    assert "Hybrid search" in response.text
