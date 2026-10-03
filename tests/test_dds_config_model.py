import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6.QtCore import QSettings, QUrl
from models.dds_config_model import DdsConfigModel, DEFAULT_XML, file_path


class DdsConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.settings = QSettings(str(Path(self.directory.name) / "config.ini"), QSettings.IniFormat)

    def test_windows_drive_file_uri_preserves_drive_and_full_path(self):
        cases = {
            r"file://D:\cyclone.xml": r"D:\cyclone.xml",
            r"file://D:\DDS settings\cyclone.xml": r"D:\DDS settings\cyclone.xml",
            "file://D:/cyclone.xml": "D:/cyclone.xml",
            "file:///D:/DDS%20settings/cyclone.xml": "D:/DDS settings/cyclone.xml",
            r"D:\cyclone.xml": r"D:\cyclone.xml",
            "file://server/share/cyclone.xml": "//server/share/cyclone.xml",
        }
        for uri, expected in cases.items():
            with self.subTest(uri=uri):
                self.assertEqual(file_path(uri).replace("\\", "/"), expected.replace("\\", "/"))

    def test_windows_file_uri_load_reload_and_autosave_use_full_path(self):
        path = Path(self.directory.name) / "cyclone.xml"
        path.write_text(DEFAULT_XML, encoding="utf-8")
        env = {"CYCLONEDDS_URI": r"file://D:\cyclone.xml"}

        def resolve_path(value):
            self.assertEqual(value, r"D:\cyclone.xml")
            return path

        # Redirect Windows filesystem access to a temporary file on any host.
        with patch("models.dds_config_model.Path", side_effect=resolve_path):
            model = DdsConfigModel(self.settings, env)
            self.assertEqual(model.status, "")
            self.assertEqual(model.editorXml, DEFAULT_XML)
            self.assertTrue(model.editorWritable)
            self.assertEqual(model.reloadEditor(), DEFAULT_XML)
            self.assertTrue(model.saveEditor("<CycloneDDS/>"))
        self.assertEqual(path.read_text(encoding="utf-8"), "<CycloneDDS/>")
        self.assertEqual(env["CYCLONEDDS_URI"], r"file://D:\cyclone.xml")

    def test_shutdown_blocks_late_autosave_after_settings_destruction(self):
        import shiboken6
        model = DdsConfigModel(self.settings, {})
        self.assertTrue(model.save(DEFAULT_XML))
        model.shutdown()
        shiboken6.delete(self.settings)
        self.assertFalse(model.saveEditor("<CycloneDDS/>"))
        self.assertFalse(model.save("<CycloneDDS/>"))

    def test_saved_xml_only_applies_on_next_start_and_overrides_environment(self):
        env = {"CYCLONEDDS_URI": "<CycloneDDS/>"}
        current = DdsConfigModel(self.settings, env)
        self.assertTrue(current.save(DEFAULT_XML))
        self.assertEqual(env["CYCLONEDDS_URI"], "<CycloneDDS/>")
        next_start = DdsConfigModel(self.settings, env)
        self.assertEqual(env["CYCLONEDDS_URI"], DEFAULT_XML)
        self.assertEqual(next_start.editorXml, DEFAULT_XML)

    def test_invalid_xml_does_not_replace_saved_config(self):
        model = DdsConfigModel(self.settings, {})
        model.save(DEFAULT_XML)
        for xml in ("<CycloneDDS>", "<wrong/>", ""):
            self.assertFalse(model.save(xml))
        self.assertEqual(self.settings.value(model.XML_KEY), DEFAULT_XML)

    def test_file_uri_with_spaces_is_loaded_but_not_modified(self):
        path = Path(self.directory.name) / "DDS settings.xml"
        path.write_text(DEFAULT_XML)
        env = {"CYCLONEDDS_URI": QUrl.fromLocalFile(str(path)).toString()}
        model = DdsConfigModel(self.settings, env)
        self.assertEqual(model.editorXml, DEFAULT_XML)
        model.save("<CycloneDDS/>")
        self.assertEqual(path.read_text(), DEFAULT_XML)

    def test_reset_restores_next_process_environment(self):
        env = {"CYCLONEDDS_URI": DEFAULT_XML}
        model = DdsConfigModel(self.settings, env)
        model.save("<CycloneDDS/>")
        model.useStartupConfiguration()
        next_start = DdsConfigModel(self.settings, env)
        self.assertEqual(next_start.activeUri, DEFAULT_XML)

    def test_corrupt_saved_config_does_not_block_editor_or_replace_environment(self):
        self.settings.setValue(DdsConfigModel.ENABLED_KEY, True)
        self.settings.setValue(DdsConfigModel.XML_KEY, "<broken>")
        env = {"CYCLONEDDS_URI": DEFAULT_XML}
        model = DdsConfigModel(self.settings, env)
        self.assertEqual(env["CYCLONEDDS_URI"], DEFAULT_XML)
        self.assertIn("not applied", model.status)
        self.assertEqual(model.editorXml, "<broken>")

    def test_environment_file_is_displayed_as_path(self):
        path = Path(self.directory.name) / "config.xml"
        path.write_text(DEFAULT_XML)
        model = DdsConfigModel(self.settings, {"CYCLONEDDS_URI": str(path)})
        self.assertIn(str(path), model.activeSummary)
        self.assertEqual(model.startupSummary, str(path))
        self.assertEqual(model.selectedSource, "environment")
        self.assertNotIn("<CycloneDDS", model.activeSummary)

    def test_return_to_initial_source_clears_restart_notice(self):
        model = DdsConfigModel(self.settings, {})
        model.save(DEFAULT_XML)
        self.assertTrue(model.restartRequired)
        model.useStartupConfiguration()
        self.assertFalse(model.restartRequired)
        self.assertEqual(model.selectedSource, "environment")

    def test_managed_xml_roundtrips_special_characters_in_qsettings(self):
        xml = '<CycloneDDS>\n<!-- Grüße &amp; "quotes" \\ paths -->\n</CycloneDDS>'
        model = DdsConfigModel(self.settings, {})
        self.assertEqual(model.selectedSource, "environment")
        self.assertTrue(model.save(xml))
        reopened = QSettings(self.settings.fileName(), QSettings.IniFormat)
        env = {}
        restarted = DdsConfigModel(reopened, env)
        self.assertEqual(restarted.editorXml, xml)
        self.assertEqual(env["CYCLONEDDS_URI"], xml)
        restarted.useStartupConfiguration()
        restarted_again = DdsConfigModel(reopened, {})
        self.assertEqual(restarted_again.selectedSource, "environment")
        self.assertEqual(restarted_again.editorXml, xml)
        self.assertTrue(restarted_again.useManagedConfiguration())

    def test_editor_autosave_respects_selected_storage(self):
        path = Path(self.directory.name) / "external.xml"
        path.write_text(DEFAULT_XML)
        model = DdsConfigModel(self.settings, {"CYCLONEDDS_URI": str(path)})
        self.assertTrue(model.editorWritable)
        self.assertTrue(model.saveEditor("<CycloneDDS/>"))
        self.assertEqual(path.read_text(), "<CycloneDDS/>")
        self.assertEqual(model.selectedSource, "environment")
        self.assertFalse(model.saveEditor("<broken>"))
        self.assertEqual(path.read_text(), "<CycloneDDS/>")
        model.useManagedConfiguration()
        self.assertTrue(model.saveEditor(DEFAULT_XML))
        self.assertEqual(path.read_text(), "<CycloneDDS/>")
        model.useStartupConfiguration()
        self.assertEqual(model.reloadEditor(), "<CycloneDDS/>")
        model.useManagedConfiguration()
        self.assertEqual(model.editorXml, DEFAULT_XML)


if __name__ == "__main__":
    unittest.main()
