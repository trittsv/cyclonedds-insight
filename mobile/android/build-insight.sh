#!/bin/sh
# Build the actual Insight application, including its QML UI and DDS Python API.
set -eu
build_mode=${1:-debug}
case "$build_mode" in
    debug|aab) ;;
    *) echo "Usage: sh mobile/android/build-insight.sh [debug|aab]" >&2; exit 2 ;;
esac
android_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$android_dir/../.." && pwd)
export VIRTUAL_ENV="$android_dir/.venv311"
export PATH="$VIRTUAL_ENV/bin:$PATH"
export INSIGHT_SOURCE_ROOT="$repo_dir"
export VERSION_python3=3.11.11
export VERSION_hostpython3=3.11.11
sdk_dir=${ANDROID_SDK_ROOT:-/Users/sventrittler/Library/Android/sdk}
ndk_dir=${ANDROID_NDK_HOME:-"$sdk_dir/ndk/27.2.12479018"}
pyside_wheel=${PYSIDE_ANDROID_WHEEL:-"$HOME/Downloads/pyside6-6.11.0-6.11.0-cp311-cp311-android_aarch64.whl"}
shiboken_wheel=${SHIBOKEN_ANDROID_WHEEL:-"$HOME/Downloads/shiboken6-6.11.0-6.11.0-cp311-cp311-android_aarch64.whl"}
if [ -z "${JAVA_HOME:-}" ] && [ -d "$HOME/Library/Java/JavaVirtualMachines/jdk-17.0.2+8/Contents/Home" ]; then
    export JAVA_HOME="$HOME/Library/Java/JavaVirtualMachines/jdk-17.0.2+8/Contents/Home"
fi
test -f "$pyside_wheel"
test -f "$shiboken_wheel"
dds_source="$repo_dir/build/android-cyclonedds-upstream"
dds_revision=552fb2e4cf180e4702c9aa52b99212ba47389588
if [ ! -d "$dds_source" ]; then
    git clone --branch fix/ios-hostname-raw-ethernet https://github.com/trittsv/cyclonedds.git "$dds_source"
    git -C "$dds_source" checkout --detach "$dds_revision"
fi
if [ "$(git -C "$dds_source" rev-parse HEAD)" != "$dds_revision" ]; then
    echo "Unexpected CycloneDDS revision in $dds_source; expected $dds_revision" >&2
    exit 1
fi
cmake --fresh -S "$dds_source" -B "$repo_dir/build/android-dds" \
    -DCMAKE_TOOLCHAIN_FILE="$ndk_dir/build/cmake/android.toolchain.cmake" \
    -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-28 \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_IDLC=OFF -DBUILD_DDSPERF=OFF \
    -DBUILD_TESTING=OFF -DENABLE_SSL=OFF -DENABLE_SECURITY=OFF \
    -DCMAKE_INSTALL_PREFIX="$repo_dir/build/android-dds/install"
cmake --build "$repo_dir/build/android-dds" --parallel 8 --target install
python "$android_dir/prepare-insight.py"
cd "$repo_dir/build/android-insight"
if [ ! -f buildozer.spec ]; then
    pyside6-android-deploy --init --keep-deployment-files --name insight \
        --wheel-pyside "$pyside_wheel" --wheel-shiboken "$shiboken_wheel" \
        --sdk-path "$sdk_dir" --ndk-path "$ndk_dir"
fi
python "$android_dir/configure-insight.py"
if [ "$build_mode" = aab ]; then
    python -m buildozer android release
    python "$android_dir/verify-apk.py" "$repo_dir/dist/android/cycloneddsinsight-0.1-arm64-v8a-release.aab"
else
    python -m buildozer android debug
    python "$android_dir/verify-apk.py" "$repo_dir/dist/android/cycloneddsinsight-0.1-arm64-v8a-debug.apk"
fi
