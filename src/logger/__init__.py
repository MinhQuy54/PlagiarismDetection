"""Logger module for Plagiarism Detection Service."""

from .file_logger import FileLogger, init_file_logger, get_file_logger
from .interceptor import LoggingInterceptor

__all__ = [
    "FileLogger",
    "init_file_logger",
    "get_file_logger",
    "LoggingInterceptor",
]
