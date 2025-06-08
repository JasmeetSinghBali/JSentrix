"""
Tracing setup for the MCP Server service.
- Automatically instruments FastAPI routes.
- Provides a tracer for custom spans.

Usage:
    from tracers.tracing import get_tracer

    def my_custom_logic():
        tracer = get_tracer()
        with tracer.start_as_current_span("my_custom_logic"):
            ...
"""

import os
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

_tracer = None

def setup_tracing(app):
    """
    Set up OpenTelemetry tracing for FastAPI app and log traces to stdout.
    Args:
        app: FastAPI app instance
    Returns:
        tracer: Tracer object for creating custom spans
    """
    global _tracer
    provider = TracerProvider()
    console_exporter = ConsoleSpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(console_exporter))
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)
    _tracer = trace.get_tracer("mcp_server")
    return _tracer

def get_tracer():
    """
    Returns the tracer instance for custom span creation.
    """
    return _tracer
