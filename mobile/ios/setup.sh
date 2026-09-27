#!/bin/sh
# Isolated host tools and physical-device wheels; no desktop/Android changes.
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
cd "$repo_dir"
tools_dir="$repo_dir/build/ios-tools"
mkdir -p "$tools_dir/wheels"
"${IOS_HOST_PYTHON:-python3.13}" -m venv "$tools_dir/venv"
"$tools_dir/venv/bin/python" -m pip install --pre \
    --index-url https://download.qt.io/snapshots/ci/pyside/dev/latest/ \
    --extra-index-url https://pypi.org/simple \
    PySide6-Essentials==6.12.0a1.dev1790410615 \
    PySide6-Addons==6.12.0a1.dev1790410615 \
    jinja2==3.1.6 pkginfo==1.13 packaging==26.3 tqdm==4.70.1 \
    loguru==0.7.3 requests==2.34.2 urllib3==2.8.0 idna==3.20 \
    certifi==2026.7.22 charset-normalizer==3.5.1

download() {
    url=$1 destination=$2 checksum=$3
    if [ ! -f "$destination" ]; then
        curl -fL --retry 2 "$url" -o "$destination.part"
        mv "$destination.part" "$destination"
    fi
    echo "$checksum  $destination" | shasum -a 256 -c -
}
base=https://download.qt.io/snapshots/ci/pyside/dev/latest
pyside=pyside6-6.12.0a1-6.12.1-cp315-cp315-ios_arm64.whl
shiboken=shiboken6-6.12.0a1-6.12.1-cp315-cp315-ios_arm64.whl
download "$base/pyside6/$pyside" "$tools_dir/wheels/$pyside" \
    cbb53b303f64bcfa12cbff8dc3bfde117826b3a6738d41a51a0c8100a680d6b1
download "$base/shiboken6/$shiboken" "$tools_dir/wheels/$shiboken" \
    3a8da262e97486b1e80be899aeb6815eeb2d211c7d38fc2294b07db76ac9d63b
download https://www.python.org/ftp/python/3.15.0/python-3.15.0rc2-iOS-XCframework.tar.gz \
    "$tools_dir/python-ios.tar.gz" \
    2496d92689da625cd349e856e17b3d540787f8d17806e21536e8d394d940adc0
if [ ! -d "$tools_dir/Python.xcframework" ]; then
    tar -xzf "$tools_dir/python-ios.tar.gz" -C "$tools_dir"
fi
