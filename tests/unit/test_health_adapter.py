"""Unit tests for the reference health adapter."""
from adapters.health.health_adapter import LocalHealthAdapter
from sdk.common.health import HealthCheck, HealthRegistry, HealthStatus


def _registry_with(status: HealthStatus) -> HealthRegistry:
    registry = HealthRegistry(version="1.0.0")

    @registry.register
    def database() -> HealthCheck:
        return HealthCheck(name="database", status=status, message="probe")

    return registry


def test_report_aggregates_checks():
    adapter = LocalHealthAdapter(_registry_with(HealthStatus.HEALTHY))
    report = adapter.report()
    assert report["status"] == "healthy"
    assert report["checks"]["database"]["status"] == "healthy"


def test_report_reflects_degraded():
    adapter = LocalHealthAdapter(_registry_with(HealthStatus.DEGRADED))
    assert adapter.report()["status"] == "degraded"


def test_check_lookup():
    adapter = LocalHealthAdapter(_registry_with(HealthStatus.HEALTHY))
    assert adapter.check("database")["message"] == "probe"
    assert adapter.check("missing") is None
