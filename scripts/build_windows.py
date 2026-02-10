"""
PyInstaller build script for Windows executable.

Creates a standalone .exe file that bundles the RAG application
with all dependencies.

Usage:
    python scripts/build_windows.py

Requirements:
    pip install pyinstaller
"""

import os
import sys
import subprocess
from pathlib import Path


def run_command(cmd: list, cwd: str = None) -> bool:
    """Run a command and return True if successful."""
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=cwd)
    return result.returncode == 0


def build_windows_exe():
    """Build Windows executable with PyInstaller."""

    project_root = Path(__file__).parent.parent
    dist_dir = project_root / "dist"
    build_dir = project_root / "build"

    print("=" * 60)
    print("Building RAG Knowledge Base - Windows Edition")
    print("=" * 60)
    print()

    # Clean previous builds
    if dist_dir.exists():
        print("Cleaning dist directory...")
        for item in dist_dir.iterdir():
            if item.is_dir() and "RAG" in item.name:
                import shutil
                shutil.rmtree(item)

    if build_dir.exists():
        print("Cleaning build directory...")
        import shutil
        shutil.rmtree(build_dir)

    # PyInstaller command
    pyinstaller_cmd = [
        "pyinstaller",
        "--name=RAG-Knowledge-Base",
        "--onefile",  # Create single exe
        "--windowed",  # No console window (hide terminal)
        "--icon=assets/icon.ico" if (project_root / "assets/icon.ico").exists() else "",
        "--add-data=src;src",  # Include src directory
        "--add-data=.env.example;.",  # Include example config
        "--hidden-import=asyncpg",
        "--hidden-import=pgvector",
        "--hidden-import=pydantic_ai",
        "--hidden-import=streamlit",
        "--hidden-import=streamlit_chat",
        "--hidden-import=natasha",
        "--collect-all=natasha",
        "--collect-all=pymorphy3",
        "--noconfirm",  # Replace existing build
        "src/web_ui.py",  # Entry point
    ]

    # Remove empty strings
    pyinstaller_cmd = [arg for arg in pyinstaller_cmd if arg]

    print()
    print("Running PyInstaller...")
    print("-" * 60)

    if not run_command(pyinstaller_cmd, cwd=str(project_root)):
        print()
        print("❌ Build failed!")
        print("Make sure PyInstaller is installed: pip install pyinstaller")
        return False

    print()
    print("-" * 60)
    print("✅ Build successful!")
    print()
    print(f"Executable: {dist_dir / 'RAG-Knowledge-Base.exe'}")
    print()

    # Create portable package
    portable_dir = dist_dir / "RAG-Knowledge-Base-Windows"
    portable_dir.mkdir(exist_ok=True)

    import shutil
    shutil.copy(dist_dir / "RAG-Knowledge-Base.exe", portable_dir / "RAG-Knowledge-Base.exe")

    # Copy README and templates
    readme_dest = portable_dir / "README.txt"
    with open(readme_dest, "w", encoding="utf-8") as f:
        f.write("""RAG Knowledge Base - Windows Edition
=====================================

Quick Start:
1. Double-click RAG-Knowledge-Base.exe
2. A browser window will open automatically
3. Configure your API keys in the settings sidebar
4. Add documents to the 'documents' folder
5. Run ingestion from the Documents page

Configuration:
- Settings are managed through the web interface
- API keys and models can be changed in real-time
- No manual .env editing required

System Requirements:
- Windows 10 or later
- Internet connection for API calls
- PostgreSQL database (local or remote)

Documentation:
https://github.com/yourusername/MongoDB-RAG-Agent

Support:
For issues and questions, please open a GitHub issue.
""")

    print(f"Portable package: {portable_dir}")
    print()
    print("To distribute:")
    print("1. Zip the RAG-Knowledge-Base-Windows folder")
    print("2. Share the zip file with users")
    print("3. Users just need to extract and run the exe")
    print()

    return True


if __name__ == "__main__":
    # Check Python version
    if sys.version_info < (3, 10):
        print("❌ Python 3.10 or higher is required")
        sys.exit(1)

    # Check PyInstaller
    try:
        import PyInstaller
        print(f"PyInstaller version: {PyInstaller.__version__}")
    except ImportError:
        print("❌ PyInstaller not found")
        print("Install with: pip install pyinstaller")
        sys.exit(1)

    build_windows_exe()
