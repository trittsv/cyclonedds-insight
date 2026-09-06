#!/bin/sh
set -eu
android_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
repo_dir=$(CDPATH= cd -- "$android_dir/../.." && pwd)
ndk_dir=${ANDROID_NDK_HOME:-/Users/sventrittler/Library/Android/sdk/ndk/27.2.12479018}
export PATH="$android_dir/.venv311/bin:$PATH"
export VIRTUAL_ENV="$android_dir/.venv311"
export INSIGHT_SOURCE_ROOT="$repo_dir"
export VERSION_python3=3.11.11
export VERSION_hostpython3=3.11.11
if [ -z "${JAVA_HOME:-}" ] && [ -d /Users/sventrittler/Library/Java/JavaVirtualMachines/jdk-17.0.2+8/Contents/Home ]; then
    export JAVA_HOME=/Users/sventrittler/Library/Java/JavaVirtualMachines/jdk-17.0.2+8/Contents/Home
fi
cmake -S "$repo_dir/deps/cyclonedds" -B "$repo_dir/build/android-dds" \
    -DCMAKE_TOOLCHAIN_FILE="$ndk_dir/build/cmake/android.toolchain.cmake" \
    -DANDROID_ABI=arm64-v8a -DANDROID_PLATFORM=android-28 \
    -DCMAKE_BUILD_TYPE=Release -DBUILD_IDLC=OFF -DBUILD_DDSPERF=OFF \
    -DBUILD_TESTING=OFF -DENABLE_SSL=OFF -DENABLE_SECURITY=OFF \
    -DCMAKE_INSTALL_PREFIX="$repo_dir/build/android-dds/install"
cmake --build "$repo_dir/build/android-dds" --parallel 8 --target install
if [ ! -f "$android_dir/smoke/buildozer.spec" ]; then
    sh "$android_dir/build-probe.sh" --init
fi
python "$android_dir/configure-dds.py"
cd "$android_dir/smoke"
python -m buildozer android debug
python "$android_dir/verify-apk.py"
