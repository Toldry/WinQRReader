"""
Release Archive Packager for WinQRReader
Packs the PyInstaller output in dist/WinQRReader into the release asset for the
current OS: a .zip on Windows, a .tar.gz elsewhere (tar keeps the executable bit,
which zip archives lose). Under GitHub Actions, exports ARCHIVE_NAME via GITHUB_ENV.
"""
import argparse
import os
import sys
import tarfile
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DIST_APP_DIR = BASE_DIR / "dist" / "WinQRReader"


def create_zip(archive_path: Path):
    """Zip the bundle contents at the archive root, like Compress-Archive dist/WinQRReader/*."""
    with zipfile.ZipFile(archive_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for file_path in sorted(DIST_APP_DIR.rglob("*")):
            archive.write(file_path, file_path.relative_to(DIST_APP_DIR))


def create_tarball(archive_path: Path):
    """Tar the bundle under a top-level WinQRReader/ directory, preserving file modes."""
    with tarfile.open(archive_path, "w:gz") as archive:
        archive.add(DIST_APP_DIR, arcname=DIST_APP_DIR.name)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.strip().splitlines()[0])
    parser.add_argument("--tag", default="", help="Release tag, e.g. v1.0.0 (default: latest)")
    parser.add_argument("--platform", required=True, help="Platform suffix, e.g. windows-x64 or linux-x64")
    args = parser.parse_args()

    if not DIST_APP_DIR.is_dir():
        print(f"[ERROR] {DIST_APP_DIR} not found. Run build_exe.py first.")
        return 1

    # Branch names from manual runs (e.g. feature/x) must not create subdirectories
    tag = (args.tag or "latest").replace("/", "-")
    is_windows = sys.platform == "win32"
    extension = "zip" if is_windows else "tar.gz"
    archive_name = f"WinQRReader-{tag}-{args.platform}.{extension}"
    archive_path = BASE_DIR / archive_name

    if is_windows:
        create_zip(archive_path)
    else:
        create_tarball(archive_path)
    print(f"Created release asset: {archive_name}")

    github_env_path = os.environ.get("GITHUB_ENV")
    if github_env_path:
        with open(github_env_path, "a", encoding="utf-8") as github_env:
            github_env.write(f"ARCHIVE_NAME={archive_name}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
