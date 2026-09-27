"""Build Insight for physical ARM64 iOS devices using the Qt 6.12 snapshot."""
from pathlib import Path
import argparse
import importlib.util
import json
import os
import plistlib
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "build/ios-tools"
STAGE = ROOT / "build/ios-insight"
NATIVE = ROOT / "build/ios-native"
CYCLONEDDS_REPOSITORY = "https://github.com/trittsv/cyclonedds.git"
CYCLONEDDS_BRANCH = "fix/ios-hostname-raw-ethernet"
CYCLONEDDS_REVISION = "e7a559443be3c4d4032339ab86fdccf932a7cd13"
PYTHON = TOOLS / "Python.xcframework"
BIN = Path(sys.executable).parent
os.environ["PATH"] = str(BIN) + os.pathsep + os.environ["PATH"]


def run(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def replace_once(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"Upstream changed: review patch for {path}")
    path.write_text(text.replace(old, new))


def fix_python_build_paths():
    # CPython's iOS helper must quote the marker path for app names with spaces.
    helper = PYTHON / "build/utils.sh"
    text = helper.read_text()
    old = '> ${FULL_EXT%.so}.fwork'
    new = '> "${FULL_EXT%.so}.fwork"'
    if old in text:
        helper.write_text(text.replace(old, new))
    elif new not in text:
        raise RuntimeError("Upstream changed: review Python framework marker creation")


def native():
    upstream = ROOT / "build/ios-cyclonedds-upstream"
    if not upstream.exists():
        run("git", "clone", "--branch", CYCLONEDDS_BRANCH, CYCLONEDDS_REPOSITORY, upstream)
        run("git", "checkout", "--detach", CYCLONEDDS_REVISION, cwd=upstream)
    revision = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=upstream, text=True).strip()
    if revision != CYCLONEDDS_REVISION:
        raise RuntimeError(f"Expected Cyclone DDS {CYCLONEDDS_REVISION}, found {revision} in {upstream}")
    source = ROOT / "build/ios-cyclonedds-source"
    if source.exists():
        shutil.rmtree(source)  # Recreate generated sources from the pinned branch revision.
    shutil.copytree(upstream, source, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(".git", "build", "install"))
    run("cmake", "-S", source, "-B", NATIVE,
        "-DCMAKE_SYSTEM_NAME=iOS", "-DCMAKE_OSX_SYSROOT=iphoneos",
        "-DCMAKE_OSX_ARCHITECTURES=arm64", "-DCMAKE_OSX_DEPLOYMENT_TARGET=18.0",
        "-DCMAKE_BUILD_TYPE=Release", "-DBUILD_SHARED_LIBS=OFF",
        "-DEXPORT_ALL_SYMBOLS=ON", "-DBUILD_IDLC=OFF", "-DBUILD_DDSPERF=OFF",
        "-DBUILD_TESTING=OFF", "-DENABLE_SSL=OFF", "-DENABLE_SECURITY=OFF",
        f"-DCMAKE_INSTALL_PREFIX={NATIVE / 'install'}")
    run("cmake", "--build", NATIVE, "--parallel", "8", "--target", "install")
    hostname_object = NATIVE / "src/core/CMakeFiles/ddsc.dir/__/ddsrt/src/sockets/ios/gethostname.mm.o"
    symbols = subprocess.check_output(["xcrun", "nm", "-u", hostname_object], text=True)
    if "_OBJC_CLASS_$_UIDevice" not in symbols or " U _gethostname\n" in symbols:
        raise RuntimeError("Cyclone DDS must use UIDevice for the iOS hostname")
    clayer = ROOT / "deps/cyclonedds-python/clayer"
    patched = NATIVE / "pysertype.c"
    shutil.copy2(clayer / "pysertype.c", patched)
    replace_once(patched, "  bool ok;\n  if (info->valid_data)",
                 "  state->containers[state->count] = (ddspy_sample_container_t){0};\n"
                 "  bool ok;\n  if (info->valid_data)")
    sdk = subprocess.check_output(["xcrun", "--sdk", "iphoneos", "--show-sdk-path"], text=True).strip()
    run("xcrun", "--sdk", "iphoneos", "clang", "-arch", "arm64", "-isysroot", sdk,
        "-miphoneos-version-min=18.0", "-O2", "-c", patched,
        "-I" + str(PYTHON / "ios-arm64/Python.framework/Headers"),
        "-I" + str(NATIVE / "install/include"), "-I" + str(clayer),
        "-o", NATIVE / "clayer.o")


def stage(multicast, peers):
    if STAGE.exists():
        # Only the generated app sources; keep expensive unpacked Qt wheels.
        for entry in STAGE.iterdir():
            if entry.name == "deployment":
                continue
            if entry.is_dir():
                shutil.rmtree(entry)
            else:
                entry.unlink()
    shutil.copytree(ROOT / "src", STAGE, dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns("__pycache__", "qrc_file.py", "*.qm"))
    config = ET.Element("CycloneDDS")
    domain = ET.SubElement(config, "Domain", Id="any")
    ET.SubElement(ET.SubElement(domain, "General"), "AllowMulticast").text = "true" if multicast else "false"
    discovery = ET.SubElement(domain, "Discovery")
    ET.SubElement(discovery, "ParticipantIndex").text = "auto"
    peer_list = ET.SubElement(discovery, "Peers")
    for peer in peers:
        ET.SubElement(peer_list, "Peer", Address=peer)
    xml = ET.tostring(config, encoding="unicode")
    replace_once(STAGE / "main.py", "import os\n", f"import os\nos.environ.setdefault('CYCLONEDDS_URI', {xml!r})\n")
    resources = ET.parse(ROOT / "resources.qrc")
    for entry in resources.iter("file"):
        name = entry.text
        source = ROOT / name
        if name.endswith(".qm"):
            source = STAGE / "translations" / Path(name).name
            run(BIN / "pyside6-lrelease", ROOT / Path(name).with_suffix(".ts"), "-qm", source)
        entry.set("alias", entry.get("alias", name))
        entry.text = str(source)
    qrc = STAGE / "ios-resources.qrc"
    resources.write(qrc)
    run(BIN / "pyside6-rcc", qrc, "-o", STAGE / "qrc_file.py")
    for package in ("loguru", "requests", "urllib3", "idna", "certifi", "charset_normalizer"):
        source = Path(importlib.util.find_spec(package).origin).parent
        shutil.copytree(source, STAGE / package, ignore=shutil.ignore_patterns("__pycache__", "*.so"))
    shutil.copytree(ROOT / "deps/cyclonedds-python/cyclonedds", STAGE / "cyclonedds",
                    ignore=shutil.ignore_patterns("__pycache__", "*.so", "*.dylib", "__library__.py"))
    (STAGE / "cyclonedds/__library__.py").write_text("in_wheel = False\nlibrary_path = None\n")
    replace_once(STAGE / "cyclonedds/internal.py", "    system = platform.system()",
                 "    # DDS is statically linked and exported by the iOS executable.\n"
                 "    return ct.CDLL(None)\n\n    system = platform.system()")
    # Qt's automatic QML discovery excludes any path containing 'build'.
    files = sorted(str(p.relative_to(STAGE)) for p in STAGE.rglob("*")
                   if p.suffix in (".py", ".qml") and "deployment" not in p.relative_to(STAGE).parts)
    (STAGE / "insight.pyproject").write_text(json.dumps({"files": files}))


def project(team, multicast, device_name=False):
    import PySide6
    sys.path.insert(0, str(Path(PySide6.__file__).parent / "scripts"))
    from deploy_lib import config as deploy_config
    from deploy_lib.ios import pbxproj
    from ios_deploy import main as deploy
    # Scan only the application's QML, excluding Qt's unpacked examples/modules.
    scanner = deploy_config.run_qmlimportscanner
    deploy_config.run_qmlimportscanner = lambda project_dir, dry_run: scanner(STAGE / "views", dry_run)
    package_script = pbxproj._pyside6_packages_script
    # Qt is statically linked. Do not ship its SDK frameworks or unused dynamic
    # QtQmlFeatures extension (Insight uses QtQml, not the new decorator API).
    pbxproj._pyside6_packages_script = lambda cfg: package_script(cfg).replace(
        'rsync -a --delete', 'rsync -a --delete --delete-excluded --exclude="/Qt/lib/" '
        '--exclude="*.so" --exclude="*.o"')
    previous = Path.cwd()
    try:
        os.chdir(STAGE)
        deploy(main_file=STAGE / "main.py", name="CycloneDDS Insight",
               bundle_id="trittsv.app.cycloneddsinsight", app_version="0.1",
               wheel_pyside=TOOLS / "wheels/pyside6-6.12.0a1-6.12.1-cp315-cp315-ios_arm64.whl",
               wheel_shiboken=TOOLS / "wheels/shiboken6-6.12.0a1-6.12.1-cp315-cp315-ios_arm64.whl",
               xcframework_path=PYTHON, team_id=team or None)
    finally:
        os.chdir(previous)
        deploy_config.run_qmlimportscanner = scanner
        pbxproj._pyside6_packages_script = package_script
    out = STAGE / "deployment/ios_arm64"
    app_icon(out)
    main = out / "main.mm"
    replace_once(main, "PyObject *PyInit_Shiboken(void);",
                 "PyObject *PyInit_Shiboken(void);\nPyObject *PyInit__clayer(void);")
    replace_once(main, "    // Register all PySide6 modules before Py_Initialize.",
                 '    PyImport_AppendInittab("cyclonedds._clayer", PyInit__clayer);\n'
                 "    // Register all PySide6 modules before Py_Initialize.")
    # PySide removes spaces from generated product names; restore the app name.
    generated_project = out / "CycloneDDSInsight.xcodeproj"
    named_project = out / "CycloneDDS Insight.xcodeproj"
    if named_project.exists():
        shutil.rmtree(named_project)
    generated_project.rename(named_project)
    legacy_project = out / "Insight.xcodeproj"
    if legacy_project.exists():
        shutil.rmtree(legacy_project)
    pbx = named_project / "project.pbxproj"
    text = pbx.read_text()
    # Xcode derives its automatic scheme and archive name from the target name.
    text = text.replace("name = CycloneDDSInsight;", 'name = "CycloneDDS Insight";')
    text = text.replace("productName = CycloneDDSInsight;", 'productName = "CycloneDDS Insight";')
    text = text.replace("path = CycloneDDSInsight.app;", 'path = "CycloneDDS Insight.app";')
    text = text.replace("EXECUTABLE_NAME = CycloneDDSInsight_bin;",
                        'EXECUTABLE_NAME = "CycloneDDS Insight";')
    text = text.replace("/* CycloneDDSInsight", "/* CycloneDDS Insight")
    flags = f"-Wl,-force_load,{NATIVE / 'install/lib/libddsc.a'} {NATIVE / 'clayer.o'} -Wl,-export_dynamic "
    text = text.replace('OTHER_LDFLAGS = "$(inherited) ', 'OTHER_LDFLAGS = "$(inherited) ' + flags)
    # Archive's default strip-all removes exports used by ctypes.CDLL(None).
    text = text.replace("ENABLE_DEBUG_DYLIB = NO;",
                        "ENABLE_DEBUG_DYLIB = NO;\n\t\t\t\tSTRIP_INSTALLED_PRODUCT = NO;")
    # Qt copies only .py files. Include certificate data required by requests.
    extra = f'cp -f \\"{STAGE}/certifi/cacert.pem\\" \\"$CODESIGNING_FOLDER_PATH/certifi/cacert.pem\\"\\n'
    # Append data copy to the application package phase, after its mkdir/cp commands.
    start = text.index('/* Copy Python Packages */ =')
    end = text.index('\\n";', start)
    text = text[:end] + '\\n' + extra.removesuffix('\\n') + text[end:]
    pbx.write_text(text)
    # Register the asset catalog in Xcode's resources phase so actool produces
    # both Assets.car and the icon metadata in the final Info.plist.
    text = pbx.read_text()
    asset_ref = "A10000000000000000000001"
    asset_build = "A10000000000000000000002"
    text = text.replace("/* Begin PBXFileReference section */", "/* Begin PBXFileReference section */\n"
                        f'{asset_ref} = {{isa = PBXFileReference; lastKnownFileType = folder.assetcatalog; path = Assets.xcassets; sourceTree = "<group>"; }};')
    text = text.replace("/* Begin PBXBuildFile section */", "/* Begin PBXBuildFile section */\n"
                        f"{asset_build} = {{isa = PBXBuildFile; fileRef = {asset_ref}; }};")
    start = text.index("/* Begin PBXResourcesBuildPhase section */")
    index = text.index("files = (", start) + len("files = (")
    text = text[:index] + f"\n{asset_build}," + text[index:]
    pbx.write_text(text)
    (out / "Insight.entitlements").unlink(missing_ok=True)
    entitlements = {}
    if multicast:
        entitlements["com.apple.developer.networking.multicast"] = True
    if device_name:
        entitlements["com.apple.developer.device-information.user-assigned-device-name"] = True
    if entitlements:
        (out / "CycloneDDS Insight.entitlements").write_bytes(plistlib.dumps(entitlements))
        pbx.write_text(pbx.read_text().replace("CODE_SIGN_STYLE = Automatic;",
                       "CODE_SIGN_STYLE = Automatic;\n\t\t\t\tCODE_SIGN_ENTITLEMENTS = \"CycloneDDS Insight.entitlements\";"))
    plist = out / "Info.plist"
    info = plistlib.loads(plist.read_bytes())
    info["CFBundleDisplayName"] = "CycloneDDS Insight"
    info["CFBundleName"] = "CycloneDDS Insight"
    info["CFBundleVersion"] = "3"
    orientations = ["UIInterfaceOrientationPortrait", "UIInterfaceOrientationPortraitUpsideDown",
                    "UIInterfaceOrientationLandscapeLeft", "UIInterfaceOrientationLandscapeRight"]
    info["UISupportedInterfaceOrientations"] = orientations
    info["UISupportedInterfaceOrientations~ipad"] = orientations
    info["NSLocalNetworkUsageDescription"] = "Discover DDS participants and exchange topic data on your local network."
    for key in list(info):
        if key.startswith("NS") and key.endswith("UsageDescription") and key != "NSLocalNetworkUsageDescription":
            del info[key]
    # Required by App Store validation for APIs in the prebuilt PySide6 glue.
    info['NSContactsUsageDescription'] = 'CycloneDDS Insight does not access your contacts. Its Qt framework includes contact-access APIs, but this app does not request or use contact data.'
    info['NSBluetoothAlwaysUsageDescription'] = 'CycloneDDS Insight does not use Bluetooth. Its Qt framework includes Bluetooth permission APIs; DDS communication uses your IP network instead.'
    plist.write_bytes(plistlib.dumps(info))
    return named_project


def app_icon(out):
    from PySide6.QtCore import Qt
    from PySide6.QtGui import QImage, QPainter
    catalog = out / "Assets.xcassets"
    icon = catalog / "AppIcon.appiconset"
    icon.mkdir(parents=True, exist_ok=True)
    metadata = {"version": 1, "author": "xcode"}
    (catalog / "Contents.json").write_text(json.dumps({"info": metadata}))
    (icon / "Contents.json").write_text(json.dumps({"info": metadata, "images": [
        {"idiom": "universal", "platform": "ios", "size": "1024x1024", "filename": "AppIcon.png"}
    ]}))
    logo = QImage(str(ROOT / "res/images/cyclonedds.png"))
    if logo.isNull():
        raise RuntimeError("Cannot load CycloneDDS app icon")
    logo = logo.scaled(900, 900, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    canvas = QImage(1024, 1024, QImage.Format_RGB32)
    canvas.fill(Qt.white)
    painter = QPainter(canvas)
    painter.drawImage((1024 - logo.width()) // 2, (1024 - logo.height()) // 2, logo)
    painter.end()
    if not canvas.save(str(icon / "AppIcon.png")):
        raise RuntimeError("Cannot write iOS app icon")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--team", default=os.environ.get("IOS_TEAM_ID", ""))
    parser.add_argument("--project-only", action="store_true")
    parser.add_argument("--multicast", action="store_true", default=True,
                        help="DDS multicast is enabled by default; requires Apple's multicast entitlement")
    parser.add_argument("--no-multicast", action="store_false", dest="multicast",
                        help="Explicitly disable multicast for a unicast-only build")
    parser.add_argument("--peer", action="append", default=[], metavar="IP",
                        help="Bake a DDS peer address into the app; repeat for multiple peers")
    parser.add_argument("--user-assigned-device-name", action="store_true",
                        help="Request the personal device name; requires Apple's approved entitlement")
    args = parser.parse_args()
    fix_python_build_paths()
    native()
    stage(args.multicast, args.peer)
    xcode = project(args.team, args.multicast, args.user_assigned_device_name)
    print(f"Xcode project: {xcode}")
    if not args.project_only:
        run("xcodebuild", "-project", xcode, "-scheme", "CycloneDDS Insight", "-configuration", "Debug",
            "-sdk", "iphoneos", "-destination", "generic/platform=iOS",
            "-derivedDataPath", ROOT / "build/ios-derived", "ARCHS=arm64",
            *([f"DEVELOPMENT_TEAM={args.team}", "-allowProvisioningUpdates"] if args.team else
              ["CODE_SIGNING_ALLOWED=NO", "EXPANDED_CODE_SIGN_IDENTITY=-"]), "build")
        dest = ROOT / "dist/ios/CycloneDDS Insight.app"
        dest.parent.mkdir(parents=True, exist_ok=True)
        if dest.exists():
            shutil.rmtree(dest)
        shutil.copytree(ROOT / "build/ios-derived/Build/Products/Debug-iphoneos/CycloneDDS Insight.app", dest)
        run(sys.executable, ROOT / "mobile/ios/verify-app.py", dest)
        print(f"Built {dest} ({'signed' if args.team else 'unsigned; select your Team in Xcode to install'})")


if __name__ == "__main__":
    main()
