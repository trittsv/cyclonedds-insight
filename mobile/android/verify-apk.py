"""Fail the build if the real DDS runtime is absent from the final APK."""
import io
from pathlib import Path
import tarfile
import zipfile

apk = Path(__file__).parent / "smoke/insightandroidprobe-0.1-arm64-v8a-debug.apk"
with zipfile.ZipFile(apk) as archive:
    archive.getinfo("lib/arm64-v8a/libddsc.so")
    archive.getinfo("lib/arm64-v8a/libpython3.11.so")
    with tarfile.open(fileobj=io.BytesIO(archive.read("lib/arm64-v8a/libpybundle.so"))) as bundle:
        bundle.getmember("_python_bundle/site-packages/cyclonedds/_clayer.so")
        bundle.getmember("_python_bundle/site-packages/cyclonedds/domain.pyc")
print(f"Verified native Cyclone DDS and Python bindings in {apk}")
