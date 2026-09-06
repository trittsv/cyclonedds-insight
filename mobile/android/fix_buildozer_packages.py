"""Support slash-separated Android CLI package names in Buildozer 1.5."""
from pathlib import Path
import buildozer

target = Path(buildozer.__file__).parent / "targets" / "android.py"
old = """        for line in lines:
            if not line.strip().startswith('build-tools;'):
"""
new = """        for line in lines:
            # Modern Android CLI uses slashes instead of semicolons.
            line = line.strip().replace('build-tools/', 'build-tools;', 1)
            if not line.startswith('build-tools;'):
"""
source = target.read_text()
if new in source:
    print("Package parser is already patched.")
elif source.count(old) == 1:
    target.write_text(source.replace(old, new))
    print("Updated Buildozer package parser.")
else:
    raise SystemExit("Unexpected Buildozer source; no changes made.")
