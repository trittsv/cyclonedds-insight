"""Apply the modern SDK layout fix to the active Buildozer 1.5 environment."""
from pathlib import Path
import buildozer

target = Path(buildozer.__file__).parent / "targets" / "android.py"
old = "self.android_sdk_dir, 'tools', 'bin', 'sdkmanager')"
new = "self.android_sdk_dir, 'cmdline-tools', 'latest', 'bin', 'sdkmanager')"
source = target.read_text()
if new in source:
    print("Modern sdkmanager path is already configured.")
elif source.count(old) == 1:
    target.write_text(source.replace(old, new))
    print(f"Updated sdkmanager path in {target}")
else:
    raise SystemExit("Unexpected Buildozer source; no changes made.")
