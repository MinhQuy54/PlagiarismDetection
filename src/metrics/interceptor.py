"""gRPC interceptor for Prometheus metrics."""

import time
from typing import Callable, Any

import grpc

from .metrics import (
    grpc_requests_total,
    grpc_request_duration,
    grpc_requests_in_flight,
    grpc_errors_total,
)


class MetricsInterceptor(grpc.ServerInterceptor):
    """gRPC server interceptor that collects Prometheus metrics."""

    def __init__(self, service_name: str = "plagiarism"):
        self.service_name = service_name

    def intercept_service(
        self,
        continuation: Callable[[grpc.HandlerCallDetails], grpc.RpcMethodHandler],
        handler_call_details: grpc.HandlerCallDetails,
    ) -> grpc.RpcMethodHandler:
        """Intercept incoming RPC calls."""
        handler = continuation(handler_call_details)

        if handler is None:
            return handler

        if handler.unary_unary:
            return grpc.unary_unary_rpc_method_handler(
                self._wrap_unary_unary(handler.unary_unary, handler_call_details),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        elif handler.unary_stream:
            return grpc.unary_stream_rpc_method_handler(
                self._wrap_unary_stream(handler.unary_stream, handler_call_details),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        elif handler.stream_unary:
            return grpc.stream_unary_rpc_method_handler(
                self._wrap_stream_unary(handler.stream_unary, handler_call_details),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )
        elif handler.stream_stream:
            return grpc.stream_stream_rpc_method_handler(
                self._wrap_stream_stream(handler.stream_stream, handler_call_details),
                request_deserializer=handler.request_deserializer,
                response_serializer=handler.response_serializer,
            )

        return handler

    def _wrap_unary_unary(
        self,
        behavior: Callable,
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Callable:
        """Wrap unary-unary handler with metrics."""

        def wrapper(request: Any, context: grpc.ServicerContext) -> Any:
            method = handler_call_details.method

            # Track in-flight requests
            grpc_requests_in_flight.labels(service=self.service_name).inc()
            start_time = time.time()
            status = "OK"

            try:
                response = behavior(request, context)
                return response
            except Exception as e:
                status = "ERROR"
                # Get gRPC status code if available
                if hasattr(context, "code") and context.code():
                    status = context.code().name
                grpc_errors_total.labels(
                    service=self.service_name,
                    method=method,
                    code=status,
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                grpc_requests_in_flight.labels(service=self.service_name).dec()
                grpc_request_duration.labels(
                    service=self.service_name,
                    method=method,
                ).observe(duration)
                grpc_requests_total.labels(
                    service=self.service_name,
                    method=method,
                    status=status,
                ).inc()

        return wrapper

    def _wrap_unary_stream(
        self,
        behavior: Callable,
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Callable:
        """Wrap unary-stream handler with metrics."""

        def wrapper(request: Any, context: grpc.ServicerContext):
            method = handler_call_details.method
            grpc_requests_in_flight.labels(service=self.service_name).inc()
            start_time = time.time()
            status = "OK"

            try:
                for response in behavior(request, context):
                    yield response
            except Exception as e:
                status = "ERROR"
                grpc_errors_total.labels(
                    service=self.service_name,
                    method=method,
                    code=status,
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                grpc_requests_in_flight.labels(service=self.service_name).dec()
                grpc_request_duration.labels(
                    service=self.service_name,
                    method=method,
                ).observe(duration)
                grpc_requests_total.labels(
                    service=self.service_name,
                    method=method,
                    status=status,
                ).inc()

        return wrapper

    def _wrap_stream_unary(
        self,
        behavior: Callable,
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Callable:
        """Wrap stream-unary handler with metrics."""

        def wrapper(request_iterator, context: grpc.ServicerContext) -> Any:
            method = handler_call_details.method
            grpc_requests_in_flight.labels(service=self.service_name).inc()
            start_time = time.time()
            status = "OK"

            try:
                response = behavior(request_iterator, context)
                return response
            except Exception as e:
                status = "ERROR"
                grpc_errors_total.labels(
                    service=self.service_name,
                    method=method,
                    code=status,
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                grpc_requests_in_flight.labels(service=self.service_name).dec()
                grpc_request_duration.labels(
                    service=self.service_name,
                    method=method,
                ).observe(duration)
                grpc_requests_total.labels(
                    service=self.service_name,
                    method=method,
                    status=status,
                ).inc()

        return wrapper

    def _wrap_stream_stream(
        self,
        behavior: Callable,
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Callable:
        """Wrap stream-stream handler with metrics."""

        def wrapper(request_iterator, context: grpc.ServicerContext):
            method = handler_call_details.method
            grpc_requests_in_flight.labels(service=self.service_name).inc()
            start_time = time.time()
            status = "OK"

            try:
                for response in behavior(request_iterator, context):
                    yield response
            except Exception as e:
                status = "ERROR"
                grpc_errors_total.labels(
                    service=self.service_name,
                    method=method,
                    code=status,
                ).inc()
                raise
            finally:
                duration = time.time() - start_time
                grpc_requests_in_flight.labels(service=self.service_name).dec()
                grpc_request_duration.labels(
                    service=self.service_name,
                    method=method,
                ).observe(duration)
                grpc_requests_total.labels(
                    service=self.service_name,
                    method=method,
                    status=status,
                ).inc()

        return wrapper
