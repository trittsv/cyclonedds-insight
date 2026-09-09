#!/bin/sh
# Provision only the project's Python build environment; SDK/NDK are external.
set -eu
android_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
python3.11 -m venv "$android_dir/.venv311"
python="$android_dir/.venv311/bin/python"
"$python" -m pip install PySide6==6.11.0 buildozer==1.5.0 cython==0.29.33
"$python" -c 'import pathlib, subprocess, sys, PySide6; subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(pathlib.Path(PySide6.__file__).parent / "scripts/requirements-android.txt")])'
"$python" "$android_dir/fix_buildozer_sdkmanager.py"
"$python" "$android_dir/fix_buildozer_packages.py"
"$python" "$android_dir/fix_pyside_python_version.py"
