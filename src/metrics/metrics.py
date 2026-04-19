"""Prometheus metrics definitions and HTTP server."""

import threading
from http.server import HTTPServer
from prometheus_client import (
    Counter,
    Histogram,
    Gauge,
    Info,
    generate_latest,
    CONTENT_TYPE_LATEST,
)
from prometheus_client.core import CollectorRegistry
from http.server import BaseHTTPRequestHandler

# Create a custom registry
REGISTRY = CollectorRegistry(auto_describe=True)

# Service info
service_info = Info(
    "service",
    "Service information",
    registry=REGISTRY,
)

# gRPC metrics
grpc_requests_total = Counter(
    "grpc_requests_total",
    "Total number of gRPC requests",
    ["service", "method", "status"],
    registry=REGISTRY,
)

grpc_request_duration = Histogram(
    "grpc_request_duration_seconds",
    "Duration of gRPC requests in seconds",
    ["service", "method"],
    buckets=[0.1, 0.5, 1, 2.5, 5, 10, 30, 60, 120, 300],
    registry=REGISTRY,
)

grpc_requests_in_flight = Gauge(
    "grpc_requests_in_flight",
    "Number of gRPC requests currently being processed",
    ["service"],
    registry=REGISTRY,
)

grpc_errors_total = Counter(
    "grpc_errors_total",
    "Total number of gRPC errors",
    ["service", "method", "code"],
    registry=REGISTRY,
)

# Plagiarism-specific metrics
plagiarism_checks_total = Counter(
    "plagiarism_checks_total",
    "Total number of plagiarism checks performed",
    ["severity"],
    registry=REGISTRY,
)

plagiarism_check_duration = Histogram(
    "plagiarism_check_duration_seconds",
    "Duration of plagiarism checks in seconds",
    buckets=[1, 5, 10, 30, 60, 120, 300, 600],
    registry=REGISTRY,
)

documents_indexed_total = Counter(
    "documents_indexed_total",
    "Total number of documents indexed",
    ["status"],
    registry=REGISTRY,
)

# Elasticsearch metrics
elasticsearch_queries_total = Counter(
    "elasticsearch_queries_total",
    "Total number of Elasticsearch queries",
    ["operation"],
    registry=REGISTRY,
)

elasticsearch_query_duration = Histogram(
    "elasticsearch_query_duration_seconds",
    "Duration of Elasticsearch queries in seconds",
    ["operation"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5],
    registry=REGISTRY,
)


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for metrics endpoint."""

    def do_GET(self):
        if self.path == "/metrics":
            self.send_response(200)
            self.send_header("Content-Type", CONTENT_TYPE_LATEST)
            self.end_headers()
            self.wfile.write(generate_latest(REGISTRY))
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"OK")
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        # Suppress logging
        pass


class MetricsServer:
    """HTTP server for Prometheus metrics."""

    def __init__(self, service_name: str, port: int = 9107):
        self.service_name = service_name
        self.port = port
        self._server = None
        self._thread = None

    def start(self):
        """Start the metrics HTTP server."""
        # Set service info
        service_info.info({
            "name": self.service_name,
            "version": "1.0.0",
        })

        self._server = HTTPServer(("0.0.0.0", self.port), MetricsHandler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    def stop(self):
        """Stop the metrics server."""
        if self._server:
            self._server.shutdown()
