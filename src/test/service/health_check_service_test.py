import pytest
from src.app.service.health_check_service import HealthCheckService

def test_health_check_service_return_none():
    service = HealthCheckService()
    result = service.perform_comprehensive_health_check(None, None, None)
    assert result["status"] == "degraded"
    