"""Pin Android Python to the CPython 3.11 ABI of the downloaded Qt wheels."""
from pathlib import Path
import PySide6

target = Path(PySide6.__file__).parent / "scripts/deploy_lib/android/buildozer.py"
source = target.read_text()
old = '"python3,shiboken6,PySide6"'
new = '"python3==3.11.11,hostpython3==3.11.11,shiboken6,PySide6"'
if new in source:
    print("Android Python version is already pinned.")
elif source.count(old) == 1:
    target.write_text(source.replace(old, new))
    print("Pinned Android Python and build host Python to 3.11.11.")
else:
    raise SystemExit("Unexpected PySide6 deployment source; no changes made.")
