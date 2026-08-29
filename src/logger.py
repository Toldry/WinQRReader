"""
Application Logging Infrastructure for WinQRReader.
Provides rotating file logging, console streaming, unhandled exception hooking,
Qt message capture, and startup system diagnostics.
"""
import logging
from logging.handlers import RotatingFileHandler
import os
import platform
import sys
import threading
from typing import Optional

from .config import (
    ASSETS_DIR,
    BASE_DIR,
    LOG_FILE_PATH,
    LOGS_DIR,
    LOGO_PATH,
    USER_DATA_DIR,
)

logger = logging.getLogger("WinQRReader")


def _unhandled_exception_hook(exctype, value, tb):
    """Log uncaught exceptions to file before terminating."""
    if issubclass(exctype, KeyboardInterrupt):
        sys.__excepthook__(exctype, value, tb)
        return
    logger.critical("Uncaught top-level exception occurred:", exc_info=(exctype, value, tb))
    sys.__excepthook__(exctype, value, tb)


def _unhandled_thread_exception_hook(args):
    """Log uncaught thread exceptions to file."""
    if issubclass(args.exc_type, KeyboardInterrupt):
        return
    thread_name = args.thread.name if args.thread else "UnknownThread"
    logger.critical(
        f"Uncaught exception in thread [{thread_name}]:",
        exc_info=(args.exc_type, args.exc_value, args.exc_traceback),
    )


def install_qt_message_handler():
    """Route internal Qt warnings and errors to Python logging."""
    try:
        from PyQt6.QtCore import QtMsgType, qInstallMessageHandler

        def _qt_message_handler(mode, context, message):
            file_info = f" ({context.file}:{context.line})" if context.file else ""
            if mode == QtMsgType.QtDebugMsg:
                logger.debug(f"[Qt]{file_info} {message}")
            elif mode == QtMsgType.QtInfoMsg:
                logger.info(f"[Qt]{file_info} {message}")
            elif mode == QtMsgType.QtWarningMsg:
                logger.warning(f"[Qt]{file_info} {message}")
            elif mode == QtMsgType.QtCriticalMsg:
                logger.error(f"[Qt]{file_info} {message}")
            elif mode == QtMsgType.QtFatalMsg:
                logger.critical(f"[Qt]{file_info} {message}")

        qInstallMessageHandler(_qt_message_handler)
        logger.debug("Qt message handler installed.")
    except Exception as e:
        logger.warning(f"Could not install Qt message handler: {e}")


def setup_logging(log_level: Optional[str] = None) -> logging.Logger:
    """
    Initialize unified application logging with RotatingFileHandler and safe console streaming.
    Installs exception hooks for both main thread and worker threads.
    """
    if log_level is None:
        log_level = os.environ.get("WINQR_LOG_LEVEL", "INFO").upper()

    numeric_level = getattr(logging, log_level, logging.INFO)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Avoid duplicate handlers if setup_logging is invoked multiple times
    root_logger.handlers.clear()

    formatter = logging.Formatter(
        fmt="%(asctime)s [%(levelname)s] (%(name)s:%(lineno)d) %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 1. File Handler (Rotating log file, UTF-8, max 5 MB, 3 backups)
    try:
        LOGS_DIR.mkdir(parents=True, exist_ok=True)
        file_handler = RotatingFileHandler(
            str(LOG_FILE_PATH),
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        )
        file_handler.setLevel(numeric_level)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    except Exception as e:
        # Fallback if log directory write fails
        sys.stderr.write(f"Failed to create file logger at {LOG_FILE_PATH}: {e}\n")

    # 2. Console Handler (for interactive terminal and IDE debugging)
    try:
        if sys.stderr is not None:
            console_handler = logging.StreamHandler(sys.stderr)
            console_handler.setLevel(numeric_level)
            console_handler.setFormatter(formatter)
            root_logger.addHandler(console_handler)
    except Exception:
        pass

    # 3. Register global exception hooks
    sys.excepthook = _unhandled_exception_hook
    if hasattr(threading, "excepthook"):
        threading.excepthook = _unhandled_thread_exception_hook

    return logger


def log_system_diagnostics():
    """Log critical runtime environment information for debugging crashes and deployment issues."""
    is_frozen = getattr(sys, "frozen", False)
    exe_path = sys.executable
    cwd = os.getcwd()
    args = sys.argv

    logger.info("=" * 60)
    logger.info("WinQRReader Application Starting")
    logger.info("=" * 60)
    logger.info(f"Log File: {LOG_FILE_PATH}")
    logger.info(f"Execution Mode: {'Frozen / Standalone Bundle' if is_frozen else 'Source Script'}")
    logger.info(f"Executable: {exe_path}")
    logger.info(f"Arguments: {args}")
    logger.info(f"Working Directory: {cwd}")
    logger.info(f"Base Directory: {BASE_DIR}")
    logger.info(f"User Data Directory: {USER_DATA_DIR}")
    logger.info(f"Python Version: {sys.version.splitlines()[0]}")
    logger.info(f"Platform: {platform.platform()} ({platform.machine()})")
    logger.info(f"Assets Directory: {ASSETS_DIR} (exists: {ASSETS_DIR.exists()})")
    logger.info(f"Logo Path: {LOGO_PATH} (exists: {LOGO_PATH.exists()})")

    # Diagnostic check for shortcut pointing to build directory instead of dist
    if is_frozen or "build" in exe_path.lower():
        exe_path_obj = os.path.normpath(exe_path).lower()
        if "\\build\\" in exe_path_obj or "/build/" in exe_path_obj:
            logger.warning(
                "DIAGNOSTIC WARNING: Executable appears to be running from the intermediate 'build/' directory! "
                "PyInstaller outputs uncollected binaries in 'build/' which will crash due to missing dependencies. "
                "Ensure shortcuts point to 'dist/WinQRReader/WinQRReader.exe' instead of 'build/WinQRReader/WinQRReader.exe'."
            )

    logger.info("-" * 60)
