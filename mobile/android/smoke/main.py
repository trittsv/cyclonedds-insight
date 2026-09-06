"""Android packaging probe; deliberately independent of the desktop DDS backend."""
import sys
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from dds_probe import DdsProbe


def main():
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Insight Android Probe")
    app.setOrganizationName("CycloneDDS")
    QQuickStyle.setStyle("Material")
    engine = QQmlApplicationEngine()
    dds = DdsProbe()
    app.aboutToQuit.connect(dds.stop)
    engine.rootContext().setContextProperty("ddsProbe", dds)
    engine.load(QUrl.fromLocalFile(str(Path(__file__).with_name("Main.qml"))))
    if not engine.rootObjects():
        return 1
    if "--smoke-test" in sys.argv:
        QTimer.singleShot(250, app.quit)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
