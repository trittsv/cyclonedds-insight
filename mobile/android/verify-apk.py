"""Check native DDS, Python bindings and runtime-loadable GIF support."""
import io
from pathlib import Path
import tarfile
import zipfile
import sys

apk = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent / "smoke/insightandroidprobe-0.1-arm64-v8a-debug.apk"
with zipfile.ZipFile(apk) as archive:
    prefix = "base/" if apk.suffix == ".aab" else ""
    archive.getinfo(prefix + "lib/arm64-v8a/libddsc.so")
    archive.getinfo(prefix + "lib/arm64-v8a/libpython3.11.so")
    with tarfile.open(fileobj=io.BytesIO(archive.read(prefix + "lib/arm64-v8a/libpybundle.so"))) as bundle:
        bundle.getmember("_python_bundle/site-packages/cyclonedds/_clayer.so")
        bundle.getmember("_python_bundle/site-packages/cyclonedds/domain.pyc")
    if apk.name.startswith(("insight-", "cycloneddsinsight-")):
        # A copy inside libpybundle.so alone is not discoverable by Qt on Android.
        archive.getinfo(prefix + "lib/arm64-v8a/libplugins_imageformats_qgif_arm64-v8a.so")
        with tarfile.open(fileobj=io.BytesIO(archive.read(prefix + "assets/private.tar"))) as assets:
            for member in ("main.pyc", "qrc_file.pyc", "dds_access/dds_data.pyc", "models/graph_model.pyc"):
                assets.getmember(member)
print(f"Verified native Cyclone DDS, Python bindings and required app plugins in {apk}")
