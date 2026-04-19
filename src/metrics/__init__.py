"""Prometheus metrics for Plagiarism Detection Service."""

from .metrics import (
    MetricsServer,
    grpc_requests_total,
    grpc_request_duration,
    grpc_requests_in_flight,
    grpc_errors_total,
    plagiarism_checks_total,
    plagiarism_check_duration,
    documents_indexed_total,
    elasticsearch_queries_total,
    elasticsearch_query_duration,
)
from .interceptor import MetricsInterceptor

__all__ = [
    "MetricsServer",
    "MetricsInterceptor",
    "grpc_requests_total",
    "grpc_request_duration",
    "grpc_requests_in_flight",
    "grpc_errors_total",
    "plagiarism_checks_total",
    "plagiarism_check_duration",
    "documents_indexed_total",
    "elasticsearch_queries_total",
    "elasticsearch_query_duration",
]
