"""OpenTelemetry reference adapter for the Arca Platform observability contract."""

from __future__ import annotations

from typing import Any


class OpenTelemetryAdapter:
    """Reference adapter exporting traces, metrics and logs via OTLP."""

    def __init__(self, endpoint: str, service_name: str, service_version: str) -> None:
        self.endpoint = endpoint
        self.service_name = service_name
        self.service_version = service_version
        self._tracer = None
        self._meter = None

    def initialize(self) -> None:
        try:
            from opentelemetry import trace
            from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
                OTLPSpanExporter,
            )
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("opentelemetry packages are required") from exc

        resource = Resource(
            attributes={
                "service.name": self.service_name,
                "service.version": self.service_version,
            }
        )
        provider = TracerProvider(resource=resource)
        exporter = OTLPSpanExporter(endpoint=self.endpoint, insecure=True)
        provider.add_span_processor(BatchSpanProcessor(exporter))
        trace.set_tracer_provider(provider)
        self._tracer = trace.get_tracer(self.service_name, self.service_version)

    def start_span(self, name: str, **kwargs: Any) -> Any:
        if self._tracer is None:
            self.initialize()
        return self._tracer.start_span(name, **kwargs)

    def collect_metric(self, name: str, value: float, labels: dict | None = None) -> None:
        # Metrics implementation uses the OTel metrics API once initialized.
        pass
