from sdk.common.health import HealthCheck, HealthRegistry, HealthStatus


def test_health_registry_healthy():
    registry = HealthRegistry(version="1.0.0")

    @registry.register
    def db() -> HealthCheck:
        return HealthCheck(name="database", status=HealthStatus.HEALTHY)

    report = registry.run()
    assert report.status == HealthStatus.HEALTHY
    assert report.version == "1.0.0"


def test_health_registry_degraded():
    registry = HealthRegistry(version="1.0.0")

    @registry.register
    def db() -> HealthCheck:
        return HealthCheck(name="database", status=HealthStatus.HEALTHY)

    @registry.register
    def cache() -> HealthCheck:
        return HealthCheck(name="cache", status=HealthStatus.DEGRADED)

    report = registry.run()
    assert report.status == HealthStatus.DEGRADED
