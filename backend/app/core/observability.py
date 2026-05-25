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
    env = os.getenv("ENVIRONMENT", "development")
    otel_endpoint = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    resource = Resource.create(attributes={
        "service.name": service_name,
        "environment": env
    })

    provider = TracerProvider(resource=resource)

    if env == "production" and not otel_endpoint:
        logger.info("ENVIRONMENT is production and OTEL_EXPORTER_OTLP_ENDPOINT is not configured. Skipping span exporter initialization to avoid localhost connection failures.")
        trace.set_tracer_provider(provider)
    else:
        endpoint = otel_endpoint or "http://localhost:6006/v1/traces"
        logger.info(f"Initializing OpenTelemetry targeting Arize Phoenix collector at {endpoint}")
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
