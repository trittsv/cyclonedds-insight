"""Check the device bundle, including symbols needed by ctypes and static QML."""
from pathlib import Path
import plistlib
import subprocess
import sys

root = Path(__file__).resolve().parents[2]
app = Path(sys.argv[1]) if len(sys.argv) > 1 else root / "dist/ios/CycloneDDS Insight.app"
info = plistlib.loads((app / "Info.plist").read_bytes())
for key in ("CFBundleName", "CFBundleDisplayName", "CFBundleExecutable"):
    assert info[key] == "CycloneDDS Insight", (key, info[key])
required_orientations = {"UIInterfaceOrientationPortrait", "UIInterfaceOrientationPortraitUpsideDown",
                         "UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"}
assert set(info.get("UISupportedInterfaceOrientations~ipad", info["UISupportedInterfaceOrientations"])) == required_orientations
binary = app / info["CFBundleExecutable"]
arch = subprocess.check_output(["lipo", "-archs", binary], text=True).strip()
assert arch == "arm64", arch
platform = subprocess.check_output(["xcrun", "vtool", "-show-build", binary], text=True)
assert "platform IOS\n" in platform, platform
assert info["UIDeviceFamily"] == [1, 2], info.get("UIDeviceFamily")
assert info["NSLocalNetworkUsageDescription"]
for key in ("NSContactsUsageDescription", "NSBluetoothAlwaysUsageDescription"):
    assert info.get(key), f"Missing purpose string for bundled Qt APIs: {key}"
assert (app / "Assets.car").is_file(), "Missing compiled app icon catalog"
for key in ("CFBundleIcons", "CFBundleIcons~ipad"):
    assert info[key]["CFBundlePrimaryIcon"]["CFBundleIconName"] == "AppIcon", key
exports = subprocess.check_output(["xcrun", "dyld_info", "-exports", binary], text=True)
for symbol in ("_PyInit__clayer", "_dds_create_participant", "_dds_get_typeinfo", "_dds_write"):
    assert symbol in exports, f"Missing export: {symbol}"
symbols = subprocess.check_output(["xcrun", "nm", binary], text=True)
assert "_OBJC_CLASS_$_UIDevice" in symbols, "Missing UIKit device-name lookup"
for symbol in ("qt_static_plugin_QGifPlugin", "qt_static_plugin_QtQuick2Plugin", "qt_static_plugin_QtQuickControls2IOSStylePlugin",
               "qt_static_plugin_QtQuickControls2BasicStylePlugin"):
    assert symbol in symbols, f"Missing static QML plugin: {symbol}"
for relative in ("main.py", "qrc_file.py", "cyclonedds/internal.py", "loguru/__init__.py",
                 "requests/__init__.py", "certifi/cacert.pem", "packages/PySide6/__init__.py",
                 "Frameworks/Python.framework/Python", "Frameworks/_ctypes.framework/_ctypes"):
    assert (app / relative).is_file(), f"Missing bundle resource: {relative}"
assert not list(app.rglob("*.so")), "Unprocessed dynamic Python extensions"
print(f"OK: {app} — iOS ARM64, iPhone/iPad, DDS exports, QML plugins and Python resources")
print("Signing and execution on a physical device must be checked separately.")
