#!/usr/bin/env python3
"""
WinQRReader - zero-config launcher
Checks for uv and (on Linux) the system packages the app relies on, then starts
the app with `uv run`, which creates .venv and installs the locked dependencies
on first run. Uses only the standard library so any system python3 can run it.
"""
import ctypes.util
import os
import shutil
import subprocess
import sys

UV_INSTALL_HINTS = {
    "win32": 'powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"',
    "default": "curl -LsSf https://astral.sh/uv/install.sh | sh",
}


def find_uv():
    """Locate uv on PATH, or where its installer puts it (dock launchers may lack ~/.local/bin on PATH)."""
    uv_path = shutil.which("uv")
    if uv_path is not None:
        return uv_path
    executable_name = "uv.exe" if os.name == "nt" else "uv"
    for install_dir in ("~/.local/bin", "~/.cargo/bin"):
        candidate = os.path.join(os.path.expanduser(install_dir), executable_name)
        if os.access(candidate, os.X_OK):
            return candidate
    return None


def print_banner():
    print("=======================================================")
    print("          WinQRReader - WiFi QR Scanner")
    print("=======================================================")
    print()


def warn_about_missing_linux_packages():
    if shutil.which("nmcli") is None:
        print("[WARNING] nmcli not found. WiFi connections need NetworkManager:")
        print("          sudo apt install network-manager")

    # Qt 6.5+ needs libxcb-cursor0 for its X11 (xcb) platform plugin
    if ctypes.util.find_library("xcb-cursor") is None:
        print("[WARNING] libxcb-cursor0 not found. The window may fail to open on X11:")
        print("          sudo apt install libxcb-cursor0")


def main() -> int:
    print_banner()

    uv_path = find_uv()
    if uv_path is None:
        install_hint = UV_INSTALL_HINTS.get(sys.platform, UV_INSTALL_HINTS["default"])
        print("[ERROR] uv not found. Install it with:")
        print(f"        {install_hint}")
        return 1

    if sys.platform.startswith("linux"):
        warn_about_missing_linux_packages()

    project_dir = os.path.dirname(os.path.abspath(__file__))
    command = [uv_path, "run", "--locked", "--no-dev", "main.py", *sys.argv[1:]]

    print("Starting WinQRReader...")
    if os.name == "posix":
        # Replace this process so signals and the exit code reach the app directly
        os.chdir(project_dir)
        os.execv(uv_path, command)
    return subprocess.call(command, cwd=project_dir)


if __name__ == "__main__":
    sys.exit(main())
