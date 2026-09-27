"""Configure the full Insight app using Qt's generated Android recipes."""
import configparser
from pathlib import Path
import shutil

root = Path(__file__).resolve().parents[2]
stage = root / "build/android-insight"
path = stage / "buildozer.spec"
config = configparser.ConfigParser(interpolation=None)
config.read(path)
recipes = Path(config.get("app", "p4a.local_recipes"))
shutil.copytree(root / "mobile/android/recipes/cyclonedds", recipes / "cyclonedds", dirs_exist_ok=True)
for key, value in {
    "title": "CycloneDDS Insight",
    "version": "0.1",
    # Increase this integer for each new Google Play upload.
    "android.numeric_version": "2",
    "android.release_artifact": "aab",
    # Buildozer joins domain and name to form the Android application ID.
    "package.name": "cycloneddsinsight",
    "package.domain": "trittsv.app",
    "requirements": "python3==3.11.11,hostpython3==3.11.11,shiboken6,PySide6,cyclonedds,loguru==0.7.3,requests==2.32.3",
    "orientation": "portrait,landscape,portrait-reverse,landscape-reverse",
    "android.manifest.orientation": "fullSensor",
    "fullscreen": "0",
    "android.minapi": "28",
    "android.ndk_api": "28",
    "android.api": "36",
    "icon.filename": str(stage / "icon.png"),
    "source.exclude_dirs": "deployment,bin,__pycache__",
    "android.permissions": "INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE,CHANGE_WIFI_MULTICAST_STATE",
}.items():
    config.set("app", key, value)
args = config.get("app", "p4a.extra_args")
if "--force-build" not in args.split():
    config.set("app", "p4a.extra_args", args + " --force-build")
config.set("buildozer", "bin_dir", str(root / "dist/android"))
with path.open("w") as stream:
    config.write(stream)
