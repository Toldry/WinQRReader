"""
WinQRReader - Windows 11 WiFi QR Code Scanner
Main Application Entry Point with Single-Instance Enforcement
"""
import ctypes
import logging
import os
import sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtNetwork import QLocalServer, QLocalSocket
from PyQt6.QtWidgets import QApplication

from src.config import LOGO_PATH

# Setup Unified Logging immediately
from src.logger import install_qt_message_handler, log_system_diagnostics, setup_logging

logger = setup_logging()

from src.config import LOGO_PATH

IPC_SERVER_NAME = "WinQRReader_SingleInstance_IPC"


def set_windows_app_id():
    """Set Windows AppUserModelID for proper taskbar grouping and branding on Windows 11."""
    if os.name == "nt":
        try:
            myappid = "WinQRReader.App.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
            logger.debug(f"SetCurrentProcessExplicitAppUserModelID: {myappid}")
        except Exception as e:
            logger.warning(f"Could not set AppUserModelID: {e}")


def main():
    try:
        log_system_diagnostics()
        set_windows_app_id()

        # Enable High DPI Scaling
        if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
        if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
            QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

        logger.info("Initializing QApplication...")
        app = QApplication(sys.argv)
        app.setApplicationName("WinQRReader")
        app.setOrganizationName("WinQRReader")

        # Install Qt internal message handler
        install_qt_message_handler()

        if LOGO_PATH.exists():
            logger.info(f"Loading application window icon from {LOGO_PATH}")
            app.setWindowIcon(QIcon(str(LOGO_PATH)))
        else:
            logger.warning(f"Application icon not found at {LOGO_PATH}")

        # -------------------------------------------------------------
        # Single-Instance Enforcement via QLocalSocket / QLocalServer
        # -------------------------------------------------------------
        logger.debug(f"Checking for existing application instance via IPC: {IPC_SERVER_NAME}...")
        socket = QLocalSocket()
        socket.connectToServer(IPC_SERVER_NAME)
        if socket.waitForConnected(300):
            logger.info("Another instance of WinQRReader is already running. Activating existing instance...")
            socket.write(b"ACTIVATE\n")
            socket.flush()
            socket.waitForBytesWritten(500)
            socket.disconnectFromServer()
            logger.info("Activation signal dispatched to primary instance. Exiting secondary process.")
            sys.exit(0)

        # Start IPC server for this primary instance
        # Clean up any stale pipe/server
        logger.debug("Starting local IPC server for primary instance...")
        QLocalServer.removeServer(IPC_SERVER_NAME)
        ipc_server = QLocalServer(app)

        from src.ui.main_window import MainWindow

        logger.info("Creating MainWindow...")
        window = MainWindow()

        def handle_incoming_ipc():
            client_socket = ipc_server.nextPendingConnection()
            if client_socket:
                client_socket.waitForReadyRead(500)
                msg = bytes(client_socket.readAll()).decode("utf-8", errors="ignore").strip()
                if msg == "ACTIVATE":
                    logger.info("Received activation signal from secondary instance.")
                    window.bring_to_foreground()
                client_socket.disconnectFromServer()

        ipc_server.newConnection.connect(handle_incoming_ipc)
        if not ipc_server.listen(IPC_SERVER_NAME):
            logger.warning(f"Could not start IPC server: {ipc_server.errorString()}")
        else:
            logger.info(f"IPC server listening on {IPC_SERVER_NAME}")

        window.show()
        logger.info("MainWindow displayed. Entering Qt event loop.")

        ret = app.exec()
        logger.info(f"Qt event loop finished with return code {ret}. Performing cleanup...")
        ipc_server.close()
        QLocalServer.removeServer(IPC_SERVER_NAME)
        logger.info("WinQRReader shut down cleanly.")
        sys.exit(ret)
    except Exception as e:
        logger.critical(f"Fatal error during application startup or execution: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
