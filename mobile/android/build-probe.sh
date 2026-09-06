#!/bin/sh
set -eu
android_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
sdk_dir=${ANDROID_SDK_ROOT:-/Users/sventrittler/Library/Android/sdk}
ndk_dir=${ANDROID_NDK_HOME:-"$sdk_dir/ndk/27.2.12479018"}
export PATH="$android_dir/.venv311/bin:$PATH"
cd "$android_dir/smoke"
# PySide6 6.11.0 skips loading ndk_path from an existing config file.
exec "$android_dir/.venv311/bin/pyside6-android-deploy" \
    --keep-deployment-files \
    --name insightandroidprobe \
    --config-file pysidedeploy.spec \
    --sdk-path "$sdk_dir" \
    --ndk-path "$ndk_dir" "$@"
