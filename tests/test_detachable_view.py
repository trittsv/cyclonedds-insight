# Copyright(c) 2024 Sven Trittler
#
# This program and the accompanying materials are made available under the
# terms of the Eclipse Public License v. 2.0 which is available at
# http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
# v. 1.0 which is available at
# http://www.eclipse.org/org/documents/edl-v10.php.
#
# SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause

"""
Exercise embedded and detached view lifetime without starting DDS participants.
"""
import os
from pathlib import Path
import sys
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from PySide6.QtCore import QAbstractListModel, QMetaObject, QObject, Qt, QUrl, Signal, Slot, Q_ARG
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine, qmlRegisterModule
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest

import qrc_file


class ShapesModel(QAbstractListModel):
    shapeUpdateSignale = Signal(str, str, str, int, int, int, float, int, bool, bool)

    def rowCount(self, parent=None):
        return 0


class LoggerConfig(QObject):
    logMessage = Signal(str)
    logLevelChanged = Signal(str)

    @Slot()
    def requestCurrentLogLevel(self):
        self.logLevelChanged.emit("INFO")

    @Slot(str)
    def setGlobalLogLevel(self, level):
        self.logLevelChanged.emit(level)


class DetachableViewTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QGuiApplication.instance() or QGuiApplication([])
        qmlRegisterModule("org.eclipse.cyclonedds.insight", 1, 0)

    def setUp(self):
        self.model = ShapesModel()
        self.logger = LoggerConfig()
        self.engine = QQmlEngine()
        self.engine.rootContext().setContextProperty("loggerConfig", self.logger)
        self.engine.rootContext().setContextProperty("shapesDemoModel", self.model)
        for name, value in {
            "CYCLONEDDS_INSIGHT_VERSION": "1.0",
            "CYCLONEDDS_INSIGHT_GIT_HASH_SHORT": "1234567",
            "CYCLONEDDS_INSIGHT_GIT_HASH": "1234567890",
            "CYCLONEDDS_INSIGHT_GIT_BRANCH": "refs/heads/feature/a-long-branch-name-for-small-screens",
            "CYCLONEDDS_PYTHON_GIT_HASH_SHORT": "1234567",
            "CYCLONEDDS_PYTHON_GIT_HASH": "1234567890",
            "CYCLONEDDS_GIT_HASH_SHORT": "1234567",
            "CYCLONEDDS_GIT_HASH": "1234567890",
            "QT_VERSION": "6.10",
        }.items():
            self.engine.rootContext().setContextProperty(name, value)
        self.component = QQmlComponent(self.engine)
        self.component.setData(b"""
import QtQuick
import QtQuick.Controls
import "qrc:/src/views"
import "qrc:/src/views/shapes_demo"
ApplicationWindow {
    id: rootWindow
    width: 800
    height: 600
    visible: true
    property bool isDarkMode: false
    property int dockCount: 0
    DetachableView {
        id: host
        objectName: "host"
        anchors.fill: parent
        title: "Shapes"
        onDocked: rootWindow.dockCount++
        viewComponent: Component {
            ShapesDemoView { viewHost: host }
        }
    }
    DetachableView {
        id: aboutHost
        objectName: "aboutHost"
        anchors.fill: parent
        visible: false
        title: "About"
        viewComponent: Component {
            AboutView { viewHost: aboutHost }
        }
    }
    DetachableView {
        id: logHost
        objectName: "logHost"
        anchors.fill: parent
        visible: false
        title: "Logs"
        viewComponent: Component {
            LogView { viewHost: logHost }
        }
    }
}
""", QUrl("qrc:/DetachableViewTest.qml"))
        self.window = self.component.create()
        self.assertIsNotNone(self.window, str(self.component.errors()))
        self.host = self.window.findChild(QQuickItem, "host")
        self.view = self.host.property("viewItem")
        self.floating = self.host.findChild(QQuickWindow)
        self.log_host = self.window.findChild(QQuickItem, "logHost")
        self.log_view = self.log_host.property("viewItem")
        self.log_floating = self.log_host.findChild(QQuickWindow)
        self.about_host = self.window.findChild(QQuickItem, "aboutHost")
        self.about_view = self.about_host.property("viewItem")
        self.about_floating = self.about_host.findChild(QQuickWindow)
        QTest.qWait(30)

    def tearDown(self):
        self.invoke("shutdown")
        self.window.close()
        self.window.deleteLater()
        QTest.qWait(10)
        del self.component
        del self.engine

    def invoke(self, method):
        self.assertTrue(QMetaObject.invokeMethod(self.host, method, Qt.DirectConnection))
        QTest.qWait(20)

    def test_detach_close_and_redock_preserve_live_view(self):
        self.assertFalse(self.host.property("detached"))
        self.assertIs(self.view.window(), self.window)
        self.assertFalse(self.floating.isVisible())
        self.view.setProperty("currentControlTab", 1)
        self.view.setProperty("controlsCollapsed", True)
        self.model.shapeUpdateSignale.emit(
            "shape1", "Square", "Blue", 30, 40, 20, 0, 0, False, True)
        shape = self.view.property("shapesMap").property("shape1").toQObject()
        self.assertIsNotNone(shape)

        self.invoke("detach")
        self.assertIs(self.host.property("viewItem"), self.view)
        self.assertIs(self.view.window(), self.floating)
        self.assertTrue(self.floating.isVisible())
        self.host.setVisible(False)
        self.assertTrue(self.view.isVisible())
        self.model.shapeUpdateSignale.emit(
            "shape1", "Square", "Blue", 55, 65, 20, 0, 0, False, True)
        self.assertEqual(shape.property("x"), 55)

        self.floating.close()
        QTest.qWait(20)
        self.host.setVisible(True)
        self.assertFalse(self.host.property("detached"))
        self.assertIs(self.view.window(), self.window)
        self.assertEqual(self.window.property("dockCount"), 1)
        self.assertEqual(self.view.property("currentControlTab"), 1)
        self.assertTrue(self.view.property("controlsCollapsed"))
        self.assertIs(self.view.property("shapesMap").property("shape1").toQObject(), shape)
        self.assertEqual(shape.property("x"), 55)

        self.invoke("detach")
        self.invoke("dock")
        self.assertIs(self.host.property("viewItem"), self.view)
        self.assertIs(self.view.window(), self.window)
        self.assertFalse(self.floating.isVisible())

    def test_shutdown_does_not_redock_or_reopen_window(self):
        self.invoke("detach")
        self.invoke("shutdown")
        self.floating.close()
        self.invoke("detach")
        self.assertFalse(self.floating.isVisible())
        self.assertEqual(self.window.property("dockCount"), 0)

    def test_about_responsive_layout_and_detach(self):
        about = self.about_host
        view = self.about_view
        floating = self.about_floating
        self.host.setVisible(False)
        about.setVisible(True)
        self.assertIs(view.window(), self.window)
        self.assertFalse(floating.isVisible())
        self.window.setWidth(320)
        self.window.setHeight(280)
        QTest.qWait(30)
        scroll = view.findChild(QQuickItem, "aboutScroll")
        self.assertLessEqual(scroll.property("contentWidth"), view.width())
        self.assertGreater(scroll.property("contentHeight"), scroll.property("availableHeight"))
        self.assertTrue(QMetaObject.invokeMethod(about, "detach", Qt.DirectConnection))
        QTest.qWait(30)
        self.assertIs(view.window(), floating)
        self.assertEqual(floating.modality(), Qt.NonModal)
        floating.close()
        QTest.qWait(30)
        self.assertIs(view.window(), self.window)
        self.assertIs(about.property("viewItem"), view)
        self.assertFalse(about.property("detached"))

    def test_logs_keep_buffer_and_pause_state_when_detached(self):
        self.host.setVisible(False)
        self.log_host.setVisible(True)
        self.window.setWidth(320)
        self.window.setHeight(320)
        QTest.qWait(30)
        text = self.log_view.findChild(QQuickItem, "logTextArea")
        self.logger.logMessage.emit("before detach")
        self.assertIn("before detach", text.property("text"))
        QMetaObject.invokeMethod(self.log_view, "setAutoScroll",
                                 Qt.DirectConnection, Q_ARG("QVariant", False))
        self.logger.logMessage.emit("buffered")
        self.assertNotIn("buffered", text.property("text"))
        QMetaObject.invokeMethod(self.log_host, "detach", Qt.DirectConnection)
        QTest.qWait(30)
        self.assertIs(self.log_view.window(), self.log_floating)
        self.assertFalse(self.log_view.property("autoScrollEnabled"))
        self.logger.logMessage.emit("while detached")
        self.log_floating.close()
        QTest.qWait(30)
        self.assertIs(self.log_view.window(), self.window)
        self.assertIs(self.log_host.property("viewItem"), self.log_view)
        QMetaObject.invokeMethod(self.log_view, "setAutoScroll",
                                 Qt.DirectConnection, Q_ARG("QVariant", True))
        QTest.qWait(30)
        for message in ("before detach", "buffered", "while detached"):
            self.assertEqual(text.property("text").count(message), 1)
        self.assertEqual(self.log_view.property("logCache"), "")

    def test_small_embedded_view_scrolls(self):
        self.window.setWidth(360)
        self.window.setHeight(320)
        QTest.qWait(30)
        scroll = self.view.findChild(QQuickItem, "shapeLabScroll")
        self.assertGreater(scroll.property("contentHeight"), scroll.property("availableHeight"))


if __name__ == "__main__":
    unittest.main()
