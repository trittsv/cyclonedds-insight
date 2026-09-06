"""Add the compiled DDS library to the generated Android APK configuration."""
import configparser
import shutil
from pathlib import Path

root = Path(__file__).resolve().parents[2]
library = root / "build/android-dds/install/lib/libddsc.so"
if not library.is_file():
    raise SystemExit(f"Build Cyclone DDS first: missing {library}")
spec = root / "mobile/android/smoke/buildozer.spec"
config = configparser.ConfigParser(interpolation=None)
config.read(spec)
recipes = Path(config.get("app", "p4a.local_recipes"))
shutil.copytree(root / "mobile/android/recipes/cyclonedds", recipes / "cyclonedds", dirs_exist_ok=True)
requirements = config.get("app", "requirements").split(",")
requirements = [r for r in requirements if r.strip() not in ("android", "pyjnius")]
for dependency in ("cyclonedds",):
    if dependency not in requirements:
        requirements.append(dependency)
config.set("app", "requirements", ",".join(requirements))
extra_args = config.get("app", "p4a.extra_args", fallback="")
if "--force-build" not in extra_args.split():
    config.set("app", "p4a.extra_args", extra_args + " --force-build")
config.set("app", "android.add_libs_arm64_v8a", str(library))
config.set("app", "android.minapi", "28")
config.set("app", "android.ndk_api", "28")
permissions = {p.strip() for p in config.get("app", "android.permissions", fallback="").split(",") if p.strip()}
permissions.update(["INTERNET", "ACCESS_NETWORK_STATE", "ACCESS_WIFI_STATE", "CHANGE_WIFI_MULTICAST_STATE"])
config.set("app", "android.permissions", ",".join(sorted(permissions)))
config.set("app", "source.exclude_dirs", "deployment,bin,__pycache__")
with spec.open("w") as stream:
    config.write(stream)
print(f"Configured {spec} with {library}")
