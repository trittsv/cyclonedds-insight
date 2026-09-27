"""Desktop regression check: import app startup with iOS's missing QProcess."""
from pathlib import Path
import runpy
import sys

root = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(root / "src"))
from PySide6 import QtCore
from utils import platform_utils

platform_utils.IS_IOS = True
platform_utils.IS_MOBILE = True
if hasattr(QtCore, "QProcess"):
    del QtCore.QProcess
runpy.run_path(str(root / "src/main.py"), run_name="ios_import_check")
assert "dds_access.idlc" not in sys.modules
print("OK: all startup imports succeed without QProcess; desktop IDL compiler was not loaded")
