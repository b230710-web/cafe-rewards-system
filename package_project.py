"""
Packaging utility to generate a clean, GitHub-ready zip archive
of the Café Rewards Programme Counter project.
"""

import os
import sys
import zipfile

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ZIP_DEST = os.path.join(PROJECT_DIR, "cafe-rewards-system.zip")

EXCLUDE_EXTS = {".db", ".db-wal", ".db-shm", ".pyc", ".zip"}
EXCLUDE_DIRS = {"__pycache__", ".git", "venv", ".venv"}


def create_zip_archive():
    print(f"📦 Packaging project into: {ZIP_DEST}")
    total_files = 0

    with zipfile.ZipFile(ZIP_DEST, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(PROJECT_DIR):
            dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]

            for file in files:
                ext = os.path.splitext(file)[1]
                if ext in EXCLUDE_EXTS or file == "cafe-rewards-system.zip":
                    continue

                abs_path = os.path.join(root, file)
                rel_path = os.path.relpath(abs_path, PROJECT_DIR)
                
                archive_name = os.path.join("cafe_rewards", rel_path)
                zipf.write(abs_path, archive_name)
                total_files += 1
                print(f"  + Added: {archive_name}")

    zip_size_kb = os.path.getsize(ZIP_DEST) / 1024.0
    print(f"✅ Created {ZIP_DEST} ({total_files} files, {zip_size_kb:.1f} KB)")


if __name__ == "__main__":
    create_zip_archive()
