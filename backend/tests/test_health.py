import httpx
import pytest

from ddep_backend.main import app


@pytest.mark.asyncio
async def test_health_returns_fixed_domains() -> None:
    transport = httpx.ASGITransport(app=app)

    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        response = await client.get("/health")

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "DDEP API"
    assert [domain["label"] for domain in payload["domains"]] == [
        "기체/공력",
        "전장/하드웨어",
        "제어",
        "소프트웨어",
        "자율비행/AI",
        "제작/운용",
    ]
