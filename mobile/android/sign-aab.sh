#!/bin/sh
# Sign interactively so passwords are never placed in build logs or arguments.
set -eu
if [ "$#" -lt 2 ] || [ "$#" -gt 3 ]; then
    echo "Usage: sh mobile/android/sign-aab.sh bundle.aab upload-key.jks [alias]" >&2
    exit 2
fi
test -f "$1"
test -f "$2"
signing_alias=${3:-upload}
if [ -z "${JAVA_HOME:-}" ] && [ -d "$HOME/Library/Java/JavaVirtualMachines/jdk-17.0.2+8/Contents/Home" ]; then
    export JAVA_HOME="$HOME/Library/Java/JavaVirtualMachines/jdk-17.0.2+8/Contents/Home"
fi
signer=${JAVA_HOME:+$JAVA_HOME/bin/}jarsigner
"$signer" -keystore "$2" "$1" "$signing_alias"
"$signer" -verify "$1"
