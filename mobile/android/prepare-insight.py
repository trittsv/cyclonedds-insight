"""Stage the real application and compile Qt resources for Android packaging."""
from pathlib import Path
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[2]
stage = root / "build/android-insight"
stage.mkdir(parents=True, exist_ok=True)
shutil.copytree(root / "src", stage, dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("__pycache__", "qrc_file.py", "*.qm"))
bin_dir = Path(sys.executable).parent
resources = ET.parse(root / "resources.qrc")
for entry in resources.iter("file"):
    name = entry.text
    source = root / name
    if name.endswith(".qm"):
        source = stage / "translations" / Path(name).name
        subprocess.run([str(bin_dir / "pyside6-lrelease"), str(root / Path(name).with_suffix(".ts")),
                        "-qm", str(source)], check=True)
    if not source.is_file():
        raise SystemExit(f"Resource missing: {source}")
    entry.set("alias", entry.get("alias", name))
    entry.text = str(source)
qrc = stage / "android-resources.qrc"
resources.write(qrc)
subprocess.run([str(bin_dir / "pyside6-rcc"), str(qrc), "-o", str(stage / "qrc_file.py")], check=True)
shutil.copy2(root / "res/images/cyclonedds.png", stage / "icon.png")
print(f"Staged CycloneDDS Insight in {stage}")
