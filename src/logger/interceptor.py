"""gRPC interceptor for logging requests - compatible with Promtail/Loki."""

import time
import uuid
from typing import Any, Callable

import grpc
from google.protobuf.json_format import MessageToDict

from .file_logger import get_file_logger


class LoggingInterceptor(grpc.ServerInterceptor):
    """gRPC server interceptor that logs all requests in JSON format."""

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
        """Wrap unary-unary handler with logging."""

        def wrapper(request: Any, context: grpc.ServicerContext) -> Any:
            request_id = str(uuid.uuid4())
            start_time = time.time()
            error_msg = None
            success = True

            try:
                response = behavior(request, context)
                return response
            except Exception as e:
                error_msg = str(e)
                success = False
                raise
            finally:
                duration_ms = int((time.time() - start_time) * 1000)
                self._log_request(
                    request_id=request_id,
                    method=handler_call_details.method,
                    request=request,
                    duration_ms=duration_ms,
                    success=success,
                    error=error_msg,
                )

        return wrapper

    def _wrap_unary_stream(
        self,
        behavior: Callable,
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Callable:
        """Wrap unary-stream handler with logging."""

        def wrapper(request: Any, context: grpc.ServicerContext):
            request_id = str(uuid.uuid4())
            start_time = time.time()
            error_msg = None
            success = True

            try:
                for response in behavior(request, context):
                    yield response
            except Exception as e:
                error_msg = str(e)
                success = False
                raise
            finally:
                duration_ms = int((time.time() - start_time) * 1000)
                self._log_request(
                    request_id=request_id,
                    method=handler_call_details.method,
                    request=request,
                    duration_ms=duration_ms,
                    success=success,
                    error=error_msg,
                    request_type="unary_stream",
                )

        return wrapper

    def _wrap_stream_unary(
        self,
        behavior: Callable,
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Callable:
        """Wrap stream-unary handler with logging."""

        def wrapper(request_iterator, context: grpc.ServicerContext) -> Any:
            request_id = str(uuid.uuid4())
            start_time = time.time()
            error_msg = None
            success = True
            request_count = 0

            def counting_iterator():
                nonlocal request_count
                for request in request_iterator:
                    request_count += 1
                    yield request

            try:
                response = behavior(counting_iterator(), context)
                return response
            except Exception as e:
                error_msg = str(e)
                success = False
                raise
            finally:
                duration_ms = int((time.time() - start_time) * 1000)
                self._log_request(
                    request_id=request_id,
                    method=handler_call_details.method,
                    request=None,
                    duration_ms=duration_ms,
                    success=success,
                    error=error_msg,
                    request_type="stream_unary",
                    request_count=request_count,
                )

        return wrapper

    def _wrap_stream_stream(
        self,
        behavior: Callable,
        handler_call_details: grpc.HandlerCallDetails,
    ) -> Callable:
        """Wrap stream-stream handler with logging."""

        def wrapper(request_iterator, context: grpc.ServicerContext):
            request_id = str(uuid.uuid4())
            start_time = time.time()
            error_msg = None
            success = True
            request_count = 0

            def counting_iterator():
                nonlocal request_count
                for request in request_iterator:
                    request_count += 1
                    yield request

            try:
                for response in behavior(counting_iterator(), context):
                    yield response
            except Exception as e:
                error_msg = str(e)
                success = False
                raise
            finally:
                duration_ms = int((time.time() - start_time) * 1000)
                self._log_request(
                    request_id=request_id,
                    method=handler_call_details.method,
                    request=None,
                    duration_ms=duration_ms,
                    success=success,
                    error=error_msg,
                    request_type="stream_stream",
                    request_count=request_count,
                )

        return wrapper

    def _log_request(
        self,
        request_id: str,
        method: str,
        request: Any,
        duration_ms: int,
        success: bool,
        error: str = None,
        request_type: str = "unary_unary",
        request_count: int = None,
    ) -> None:
        """Log request to file logger."""
        file_logger = get_file_logger()

        trace_data = {
            "request_id": request_id,
            "method": method,
            "duration_ms": duration_ms,
            "success": success,
            "request_type": request_type,
        }

        # Extract request args for unary requests
        if request is not None:
            try:
                request_args = MessageToDict(
                    request,
                    preserving_proto_field_name=True,
                    including_default_value_fields=False,
                )
                # Filter empty values
                request_args = {
                    k: v for k, v in request_args.items() if v not in (None, "", [], {})
                }
                if request_args:
                    trace_data["request_args"] = request_args
            except Exception:
                pass

        # Add request count for streaming
        if request_count is not None:
            trace_data["request_count"] = request_count

        # Add error if present
        if error:
            trace_data["error"] = error

        # Write to file logger
        if file_logger is not None:
            file_logger.write_trace(trace_data)
        else:
            # Fallback to print JSON
            import json

            print(json.dumps(trace_data, ensure_ascii=False, default=str))
