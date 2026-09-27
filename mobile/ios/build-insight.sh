#!/bin/sh
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
exec "$repo_dir/build/ios-tools/venv/bin/python" "$repo_dir/mobile/ios/build.py" "$@"
