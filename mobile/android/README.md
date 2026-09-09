# Android builds

## Build the full Insight application

From the repository root:

```sh
# Only needed to provision/recreate the Android Python build environment:
sh mobile/android/setup.sh

# Stage src/, compile translations/resources, build native DDS and package:
sh mobile/android/build-insight.sh
```

The build uses the local `deps/cyclonedds` and `deps/cyclonedds-python` checkouts
from the desktop development setup. It stages the real application in
`build/android-insight` and writes the debug APK to
`dist/android/insight-0.1-arm64-v8a-debug.apk`. It has a separate
application ID (`org.eclipse.cyclonedds.insight`) and can coexist with the probe.
The launcher label is `CycloneDDS Insight`. Builds using the former ID
`trittsv.app.cycloneddsinsight` remain a separate installation; the new ID does
not update or migrate that installation's settings.

Prerequisites: Python 3.11, CMake, the existing p4a build prerequisites, JDK 17,
Android SDK platform 36, NDK 27.2.12479018, and the two PySide6/Shiboken6 6.11.0
Android ARM64 wheels. The script defaults to this Mac's SDK and Downloads paths;
override `ANDROID_SDK_ROOT`, `ANDROID_NDK_HOME`, `PYSIDE_ANDROID_WHEEL`,
`SHIBOKEN_ANDROID_WHEEL`, and `JAVA_HOME` for another machine.

```sh
"$HOME/Library/Android/sdk/platform-tools/adb" install -r \
  dist/android/insight-0.1-arm64-v8a-debug.apk
```

The full-app port retains the existing QML interface and allows sensor-based
rotation between portrait and landscape. Secondary windows have an Android
title bar with a close button and a Back shortcut. They open maximized on
Android, with system bars visible. Toolbars respect Qt's safe-area margins for
the status bar and display cutouts; window content uses Qt's automatic padding.
Discovery, endpoint details, dynamic network types and the DDS Python backend
are packaged. Local IDL compilation and the desktop self-updater are disabled
on Android. Updates are installed as APKs. Desktop startup is preserved.
Phone layout refinement, background discovery and all secondary windows still
need device validation; an APK build does not establish full feature parity.

Validation: the full APK builds and passes archive checks for the app modules,
Qt resources, native DDS library and Python binding. The staged UI loads in a
desktop Android-mode smoke check, starts discovery, and exits cleanly. The full
application has also been confirmed working on the phone by the user; the
earlier probe was verified on-device for discovery and Python-package message
exchange. The close controls and rotation changes still need device validation.

Status: the original Qt packaging probe built and ran on an Android device.
The DDS extension is experimental and still needs device verification.
The existing desktop build is unchanged.

## CycloneDDS Python probe

The native C participant was verified on Android and discovered on the LAN.
The probe now uses the upstream source package in `deps/cyclonedds-python`.
A local python-for-android recipe compiles its actual `clayer/pysertype.c`
against Android Python 3.11 and the Android Cyclone DDS headers/library, and
installs it as `cyclonedds/_clayer.so` alongside the upstream Python modules.
It generates only the platform-specific `__library__.py` loader configuration.
The source checkout is used directly; no desktop extension is copied.
The packaged loader defers the `ctypes.util` import until fallback library
search is needed. Android Python's patched search helper imports the `android`
extension, which references a WebView JNI symbol absent in the Qt bootstrap.
The APK uses an explicit `libddsc.so` path, so it does not need that search
helper or the `android`/PyJNIus packages. This small patch is applied only to
the packaged copy; the upstream source checkout remains unchanged.

Tap Start DDS, then Send sample. A successful test reports a received message
through cyclonedds-python, exercising its IDL serialization and native extension.
The topic is `InsightAndroidProbe`, type `InsightProbe::Message`, with one string
field `text`. The reader and writer also appear in desktop Insight on domain 0.
Stop releases the reader, writer, topic, and participant in that order.

The recipe supports the runtime API required for this test. It does not build
the optional IDL compiler backend (`_idlpy`) or install CLI entry points and their
`rich-click` dependencies. Porting the full Insight app still requires handling
those features and the other desktop dependencies.

The recipe also initializes each native collector sample container before
deserialization. Device crash logs exposed an upstream assertion failure in
`serdata_to_sample`: newly allocated collector storage contained an uninitialized
`usample` pointer. The build applies this fix to a generated copy of
`pysertype.c`, keeping assertions enabled and the upstream checkout unchanged.

## Build and install

Run `sh mobile/android/build-dds.sh` from the repository root, or
`sh ../build-dds.sh` from `smoke`. This uses the source in `deps/cyclonedds`,
builds `libddsc.so` for Android ARM64/API 28, generates the Qt build configuration,
adds the library and network permissions, and builds the APK through Buildozer.
Use this command for DDS builds: the original `build-probe.sh` regenerates a
configuration without the additional native library.

The Python-enabled APK built successfully. Its native `libddsc.so`, Python
modules and ARM64 `_clayer.so` were verified inside the APK. The Python API
write/read loop passed locally; this updated version still needs device testing.

Install `smoke/insightandroidprobe-0.1-arm64-v8a-debug.apk` with `adb install -r`, then tap
**Start DDS (domain 0)**. The status reports participant creation or the native
loader/DDS error. Stop DDS deletes the participant; exiting also cleans it up.
The interface uses Cyclone DDS's Python API. Keep the app foregrounded.
Participant creation alone does not prove network discovery. Check it from
desktop Insight on domain 0 on the same LAN. Multicast-lock handling and Android
lifecycle integration remain follow-up work if discovery or suspension needs it.

## Platform choice

Insight uses Python, PySide6 6.11.0 and native Cyclone DDS libraries.
Android is the first target because PySide6 provides `pyside6-android-deploy`.
Qt documents Linux and macOS build hosts, and APK/AAB output. Start with an
arm64-v8a physical Android device. Qt's iOS announcement targets PySide6 6.12;
it is not a deployment path for this repository's pinned 6.11.0 version.

References (checked September 6, 2026):
- [Qt Android deployment and prerequisites](https://doc.qt.io/qtforpython-6/deployment/deployment-pyside6-android-deploy.html)
- [PySide6 iOS announcement](https://www.qt.io/blog/python-mobile-app-development-bringing-pyside6-on-ios)

## Build the probe

1. Install a JDK, Android SDK and Android NDK matching the selected Qt release,
   following Qt's prerequisites above. Download **Android aarch64 wheels** for
   both PySide6 and Shiboken6 using the download links in that guide. Match their
   versions to the host PySide6 (6.11.0). Desktop wheels cannot substitute for
   these. If matching wheels are unavailable, cross-compile them using Qt's
   documented Linux workflow before proceeding.
2. From the repository root, create a separate build environment:

   ```sh
   cd /Users/sventrittler/workspace/forks/cyclonedds-insight
   python3.11 -m venv mobile/android/.venv311
   source mobile/android/.venv311/bin/activate
   python -m pip install PySide6==6.11.0
   python -c 'import pathlib, subprocess, sys, PySide6; subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", str(pathlib.Path(PySide6.__file__).parent / "scripts" / "requirements-android.txt")])'
   ```

3. Build from the isolated probe directory so deployment does not collect the
   desktop application's dependencies. Replace the four example paths:

   ```sh
   cd /Users/sventrittler/workspace/forks/cyclonedds-insight/mobile/android/smoke
   pyside6-android-deploy --name "Insight Android Probe" \
     --wheel-pyside /absolute/path/to/PySide6-android-aarch64.whl \
     --wheel-shiboken /absolute/path/to/shiboken6-android-aarch64.whl \
     --sdk-path /absolute/path/to/android-sdk \
     --ndk-path /absolute/path/to/android-ndk
   ```

   The tool generates local `pysidedeploy.spec` and Buildozer configuration.
   Use debug mode for the first APK. SDK installation may request license
   acceptance. Do not use the desktop `build.sh` for Android.

4. Enable Developer options and USB debugging on the phone, connect it by USB,
   authorize the computer on the phone, and install the generated APK:

   ```sh
   adb devices
   adb install -r /absolute/path/to/generated-debug.apk
   ```

   Launch Insight Android Probe and tap the touch-test button. Check portrait
   and landscape. This establishes packaging and input only, not DDS support.

For a quick desktop load check from the repository root:

```sh
QT_QPA_PLATFORM=offscreen deps/venv/bin/python mobile/android/smoke/main.py --smoke-test
```

## Work required for the real app

### Buildozer 1.5 SDK manager compatibility

When retrying an existing build, use `sh mobile/android/build-probe.sh` from
the repository root (or `sh ../build-probe.sh` from `smoke`). PySide6 6.11.0
skips loading the saved NDK path when `--config-file` is supplied; the wrapper
passes it explicitly and selects the Python 3.11 environment. It requires the
configuration generated by the first deployment command above.

If deployment fails with `javax/xml/bind/annotation/XmlSchema`, Buildozer may
be invoking the obsolete `sdk/tools/bin/sdkmanager`. With modern Android
command-line tools installed under `sdk/cmdline-tools/latest`, run this once
from the repository root in the Android build environment:

```sh
python mobile/android/fix_buildozer_sdkmanager.py
```

This patches only the active environment's Buildozer SDK manager path. It was
verified locally by invoking the selected SDK manager's `--version` (20.0).
Reapply after reinstalling Buildozer 1.5. This does not validate the full APK
build or change the installed SDK, NDK, or Java version.

### Remaining application work

1. Cross-compile `libddsc` and the CycloneDDS Python C extension for Android
   arm64 and the packaged Python version. Supply a python-for-android recipe
   and package/load the native libraries. Desktop `pip install` is insufficient.
   First verify importing CycloneDDS and creating/deleting a domain participant
   on a physical device.
2. Add Android network permissions and investigate Wi-Fi multicast reception
   (including a multicast lock where needed). Verify discovery against a desktop
   participant on the same LAN. Test explicit peers if multicast is unavailable.
3. Adapt `src/main.py` startup, which currently requires `CYCLONEDDS_HOME` outside
   a PyInstaller bundle. Use packaged library paths and app-writable storage.
4. Replace or disable desktop-only features in a clearly labelled first mobile
   version: the updater, external `idlc` execution (`src/dds_access/idlc.py`),
   and process inspection through `psutil` (`src/models/graph_model.py`). Ship
   pre-generated IDL types initially. Audit the remaining imports for packaging.
5. Integrate discovery into a touch-friendly QML screen, then adapt the desktop
   views, dialogs, file selection, and application pause/resume behavior.
6. Test real discovery and topic reading before producing a signed release.
   Store distribution additionally needs signing and current store requirements;
   the debug APK workflow above does not publish anything.

The local initial check found no `adb` on PATH and the existing deployment tool
reported missing `jinja2`, `pkginfo`, and `tqdm`. Android SDK/NDK and target wheels
still need to be provisioned before an APK build can be validated.

## Release bundle and upload signing

Build an AAB using the same staging and native-library steps as the debug APK:

```sh
sh mobile/android/build-insight.sh aab
```

Output: `dist/android/insight-0.1-arm64-v8a-release.aab`.
Without P4A release-signing environment variables, this bundle is unsigned.
Create an upload key once, outside the repository (keep a secure backup):

```sh
export JAVA_HOME="$HOME/Library/Java/JavaVirtualMachines/jdk-17.0.2+8/Contents/Home"
mkdir -p "$HOME/.android-keys"
"$JAVA_HOME/bin/keytool" -genkeypair -v -storetype JKS \
  -keystore "$HOME/.android-keys/insight-upload.jks" \
  -alias upload -keyalg RSA -keysize 2048 -validity 10000
```

Sign the bundle interactively; the script also runs signature verification:

```sh
sh mobile/android/sign-aab.sh \
  dist/android/insight-0.1-arm64-v8a-release.aab \
  "$HOME/.android-keys/insight-upload.jks" upload
```

Upload the signed AAB to Play Console with Play App Signing. An AAB cannot be
installed directly with `adb install`; use the debug APK for local testing.
Reuse your upload key for later releases and increase the Android version code
for each new Play upload. Rebuilding the unsigned bundle requires signing again.

Reference: https://developer.android.com/studio/publish/app-signing
