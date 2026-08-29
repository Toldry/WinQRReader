"""
Unit tests for application logging infrastructure and exception hooks.
"""
import logging
import sys
import threading
from pathlib import Path
import pytest

from src.config import LOG_FILE_PATH, LOGS_DIR
from src.logger import (
    _unhandled_exception_hook,
    _unhandled_thread_exception_hook,
    install_qt_message_handler,
    log_system_diagnostics,
    setup_logging,
)


def test_setup_logging_creates_file():
    """Verify setup_logging creates the log directory and file, and writes log lines."""
    test_logger = setup_logging("DEBUG")
    assert test_logger is not None
    assert LOGS_DIR.exists()

    unique_msg = "TEST_LOG_DIAGNOSTIC_ENTRY_12345"
    test_logger.info(unique_msg)

    # Flush handlers
    for handler in logging.getLogger().handlers:
        handler.flush()

    assert LOG_FILE_PATH.exists()
    content = LOG_FILE_PATH.read_text(encoding="utf-8")
    assert unique_msg in content


def test_log_system_diagnostics():
    """Verify log_system_diagnostics runs successfully and logs environment context."""
    test_logger = setup_logging("INFO")
    log_system_diagnostics()

    for handler in logging.getLogger().handlers:
        handler.flush()

    content = LOG_FILE_PATH.read_text(encoding="utf-8")
    assert "WinQRReader Application Starting" in content
    assert "Log File:" in content
    assert "Execution Mode:" in content


def test_unhandled_exception_hook():
    """Verify uncaught exception hook logs tracebacks to file."""
    setup_logging("DEBUG")

    try:
        raise ValueError("Simulated uncaught exception for logging test")
    except ValueError:
        exc_type, exc_value, tb = sys.exc_info()
        # Call hook without delegating to sys.__excepthook__ default termination
        orig_sys_hook = sys.__excepthook__
        sys.__excepthook__ = lambda *args: None
        try:
            _unhandled_exception_hook(exc_type, exc_value, tb)
        finally:
            sys.__excepthook__ = orig_sys_hook

    for handler in logging.getLogger().handlers:
        handler.flush()

    content = LOG_FILE_PATH.read_text(encoding="utf-8")
    assert "Simulated uncaught exception for logging test" in content
    assert "Uncaught top-level exception occurred:" in content


def test_unhandled_thread_exception_hook():
    """Verify thread exception hook logs thread name and traceback."""
    setup_logging("DEBUG")

    class FakeArgs:
        def __init__(self, exc_type, exc_value, exc_traceback, thread):
            self.exc_type = exc_type
            self.exc_value = exc_value
            self.exc_traceback = exc_traceback
            self.thread = thread

    try:
        raise RuntimeError("Simulated worker thread failure")
    except RuntimeError:
        exc_type, exc_value, tb = sys.exc_info()
        fake_thread = threading.Thread(name="TestWorkerThread")
        args = FakeArgs(exc_type, exc_value, tb, fake_thread)
        _unhandled_thread_exception_hook(args)

    for handler in logging.getLogger().handlers:
        handler.flush()

    content = LOG_FILE_PATH.read_text(encoding="utf-8")
    assert "Simulated worker thread failure" in content
    assert "[TestWorkerThread]" in content


def test_install_qt_message_handler():
    """Verify install_qt_message_handler runs cleanly."""
    install_qt_message_handler()
