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

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] (%(name)s) %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("WinQRReader")

IPC_SERVER_NAME = "WinQRReader_SingleInstance_IPC"


def set_windows_app_id():
    """Set Windows AppUserModelID for proper taskbar grouping and branding on Windows 11."""
    if os.name == "nt":
        try:
            myappid = "WinQRReader.App.1.0"
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass


def main():
    set_windows_app_id()

    # Enable High DPI Scaling
    if hasattr(Qt.ApplicationAttribute, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_EnableHighDpiScaling, True)
    if hasattr(Qt.ApplicationAttribute, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("WinQRReader")
    app.setOrganizationName("WinQRReader")

    if LOGO_PATH.exists():
        app.setWindowIcon(QIcon(str(LOGO_PATH)))

    # -------------------------------------------------------------
    # Single-Instance Enforcement via QLocalSocket / QLocalServer
    # -------------------------------------------------------------
    socket = QLocalSocket()
    socket.connectToServer(IPC_SERVER_NAME)
    if socket.waitForConnected(300):
        logger.info("Another instance of WinQRReader is already running. Activating existing instance...")
        socket.write(b"ACTIVATE\n")
        socket.flush()
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        sys.exit(0)

    # Start IPC server for this primary instance
    # Clean up any stale pipe/server
    QLocalServer.removeServer(IPC_SERVER_NAME)
    ipc_server = QLocalServer(app)

    from src.ui.main_window import MainWindow

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

    window.show()

    ret = app.exec()
    ipc_server.close()
    QLocalServer.removeServer(IPC_SERVER_NAME)
    sys.exit(ret)


if __name__ == "__main__":
    main()
