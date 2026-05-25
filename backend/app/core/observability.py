import os
import logging
from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

logger = logging.getLogger("observability")

def init_observability(app: FastAPI, service_name: str = "mro-tts-backend") -> None:
    """Initializes OpenTelemetry Tracer Provider targeting the local Arize Phoenix collector.

    Registers FastAPI auto-instrumentation for incoming requests.
    """
    # Arize Phoenix local collector receives OTLP/HTTP traces at /v1/traces (default port 6006)
    endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:6006/v1/traces")
    logger.info(f"Initializing OpenTelemetry targeting Arize Phoenix collector at {endpoint}")

    resource = Resource.create(attributes={
        "service.name": service_name,
        "environment": os.getenv("ENVIRONMENT", "development")
    })

    provider = TracerProvider(resource=resource)

    try:
        # Arize Phoenix local server runs OTLP over HTTP
        exporter = OTLPSpanExporter(endpoint=endpoint)
        processor = BatchSpanProcessor(exporter)
        provider.add_span_processor(processor)
        trace.set_tracer_provider(provider)
        logger.info("OpenTelemetry Tracer Provider and BatchSpanProcessor successfully initialized")
    except Exception as e:
        logger.error(f"Failed to configure OTel Tracer Provider: {e}")
        return

    # Automatically trace incoming FastAPI requests
    try:
        FastAPIInstrumentor.instrument_app(app)
        logger.info("FastAPI HTTP request auto-instrumentation registered")
    except Exception as e:
        logger.error(f"Failed to register FastAPI request auto-instrumentation: {e}")
