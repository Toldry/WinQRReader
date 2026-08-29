"""
PyInstaller Standalone Executable Builder for WinQRReader
Packages Python code, PyQt6 runtime, and assets/logo.png into an optimized, fast-startup Windows executable.
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path
from PIL import Image

BASE_DIR = Path(__file__).resolve().parent
DIST_DIR = BASE_DIR / "dist"
BUILD_DIR = BASE_DIR / "build"
ASSETS_DIR = BASE_DIR / "assets"
LOGO_PNG = ASSETS_DIR / "logo.png"
LOGO_ICO = ASSETS_DIR / "logo.ico"


def ensure_ico():
    """Ensure logo.ico exists for Windows Explorer application branding."""
    if LOGO_PNG.exists():
        try:
            img = Image.open(str(LOGO_PNG))
            img.save(str(LOGO_ICO), format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
            print("Generated assets/logo.ico from assets/logo.png")
        except Exception as e:
            print(f"Warning: Could not create ICO from PNG: {e}")


def build():
    print("=== WinQRReader PyInstaller Standalone Builder ===")

    # Step 1: Ensure icon assets are present
    ensure_ico()

    # Step 2: Build PyInstaller command arguments
    print("[1/2] Compiling standalone executable with PyInstaller (Fast-Startup Optimizations)...")

    sep = ";" if os.name == "nt" else ":"
    data_arg = f"{ASSETS_DIR}{sep}assets"

    # Only exclude large unrelated frameworks (like tkinter) without stripping standard libraries
    excluded_modules = [
        "tkinter",
        "matplotlib",
        "scipy",
        "pandas",
    ]

    pyinstaller_args = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--name=WinQRReader",
        "--windowed",
        "--noconfirm",
        "--clean",
        "--optimize=2",
        f"--add-data={data_arg}",
        f"--icon={LOGO_ICO}" if LOGO_ICO.exists() else "",
        "--hidden-import=PyQt6",
        "--hidden-import=cv2",
        "--hidden-import=zxingcpp",
        "--hidden-import=numpy",
    ]

    for mod in excluded_modules:
        pyinstaller_args.append(f"--exclude-module={mod}")

    pyinstaller_args.append("main.py")

    # Filter out empty arguments
    pyinstaller_args = [arg for arg in pyinstaller_args if arg]

    print(f"Running command: {' '.join(pyinstaller_args)}")
    result = subprocess.run(pyinstaller_args, cwd=str(BASE_DIR))

    if result.returncode == 0:
        print("\n[2/2] Build succeeded!")
        exe_path = DIST_DIR / "WinQRReader" / "WinQRReader.exe"
        if exe_path.exists():
            print(f"Executable output: {exe_path}")
        else:
            print(f"Executable directory output: {DIST_DIR / 'WinQRReader'}")
    else:
        print("\n[ERROR] PyInstaller build failed.")
        sys.exit(1)


if __name__ == "__main__":
    build()
