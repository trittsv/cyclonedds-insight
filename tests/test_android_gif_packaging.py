"""Regression check: a GIF plugin in the Python bundle is not enough on Android."""
import io
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = "libplugins_imageformats_qgif_arm64-v8a.so"


def archive_bytes(names):
    output = io.BytesIO()
    with tarfile.open(fileobj=output, mode="w") as archive:
        for name in names:
            info = tarfile.TarInfo(name)
            archive.addfile(info)
    return output.getvalue()


class AndroidGifPackagingTest(unittest.TestCase):
    def test_requires_native_plugin_in_apk_and_aab(self):
        with tempfile.TemporaryDirectory() as directory:
            for suffix in (".apk", ".aab"):
                for native_plugin in (False, True):
                    with self.subTest(suffix=suffix, native_plugin=native_plugin):
                        path = Path(directory) / ("cycloneddsinsight-test" + suffix)
                        prefix = "base/" if suffix == ".aab" else ""
                        with zipfile.ZipFile(path, "w") as package:
                            for name in ("libddsc.so", "libpython3.11.so"):
                                package.writestr(prefix + "lib/arm64-v8a/" + name, b"")
                            package.writestr(prefix + "lib/arm64-v8a/libpybundle.so",
                                             archive_bytes([
                                                 "_python_bundle/site-packages/cyclonedds/_clayer.so",
                                                 "_python_bundle/site-packages/cyclonedds/domain.pyc",
                                                 "_python_bundle/site-packages/PySide6/Qt/plugins/imageformats/" + PLUGIN,
                                             ]))
                            package.writestr(prefix + "assets/private.tar", archive_bytes([
                                "main.pyc", "qrc_file.pyc", "dds_access/dds_data.pyc",
                                "models/graph_model.pyc",
                            ]))
                            if native_plugin:
                                package.writestr(prefix + "lib/arm64-v8a/" + PLUGIN, b"")
                        result = subprocess.run(
                            [sys.executable, str(ROOT / "mobile/android/verify-apk.py"), str(path)],
                            capture_output=True, text=True)
                        self.assertEqual(result.returncode == 0, native_plugin, result.stderr)
                        if not native_plugin:
                            self.assertIn(PLUGIN, result.stderr)


if __name__ == "__main__":
    unittest.main()
