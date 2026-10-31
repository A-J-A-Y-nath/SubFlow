import pytest


def test_health_check_endpoint(client):
    """Test health check endpoint reports system and database connectivity."""
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    data = res.json
    assert data["success"] is True
    assert data["data"]["status"] == "healthy"
    assert data["data"]["database_connected"] is True


def test_dashboard_summary_empty_state(client, admin_token):
    """Test dashboard summary endpoint reports clear empty state when no records exist."""
    res = client.get("/api/v1/dashboard/summary", headers={
        "Authorization": f"Bearer {admin_token}"
    })
    assert res.status_code == 200
    data = res.json
    assert data["success"] is True
    assert "metrics" in data["data"]
    assert data["data"]["metrics"]["active_subscriptions"]["count"] == 0
    assert data["data"]["metrics"]["total_revenue"]["amount"] == 0.0
    assert data["data"]["is_empty"] is True
