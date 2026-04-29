from fastapi.testclient import TestClient

from app.main import app
from app.models.data_batches import GdcBatchStartRequest


def test_integrations_status_does_not_expose_secret_values() -> None:
    client = TestClient(app)

    response = client.get("/integrations/status")

    assert response.status_code == 200
    payload = response.json()
    names = {item["name"] for item in payload["integrations"]}
    assert names == {"Hugging Face", "Groq AI", "Zerve AI", "Firecrawl", "Tinyfish"}
    assert "hf_" not in response.text
    assert "fc-" not in response.text
    assert "sk-" not in response.text


def test_gdc_batch_request_limit_is_bounded() -> None:
    request = GdcBatchStartRequest(limit=10)

    assert request.limit == 10
    assert request.prefer_dx is True
