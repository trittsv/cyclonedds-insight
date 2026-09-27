"""Exercise writer editor model returns through the QML metacall boundary."""
import os
import sys
import unittest
from types import SimpleNamespace
from pathlib import Path
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from PySide6.QtCore import QObject, Slot, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlEngine, QQmlComponent
from models.tester_model import TesterModel, SequenceItem
from models.data_tree_model import DataTreeNode, DataTreeModel


class Repository(QObject):
    @Slot(str, int, str, str, int, str, object, object)
    def createEndpointFromTester(self, *args):
        pass


class Handler:
    def getRootNode(self, topic):
        root = DataTreeNode("", topic, 0)
        root.dataType = SimpleNamespace(value="")
        root.appendChild(DataTreeNode("value", "str", DataTreeModel.IsStrRole, parent=root))
        return root


class EditorReturns(unittest.TestCase):
    def test_writer_and_sequence_returns(self):
        app = QGuiApplication.instance() or QGuiApplication([])
        repo = Repository()
        model = TesterModel({}, Handler(), repo)
        model.alreadyConnectedDomains.append(0)
        model.addWriter("writer", 0, "Topic", "Message", {})
        model.items["sequence"] = SequenceItem("Sequence", parent=model)
        engine = QQmlEngine()
        engine.rootContext().setContextProperty("tester", model)
        component = QQmlComponent(engine)
        component.setData(b'''import QtQuick
Item {
    width: 400; height: 300
    property var tree: tester.getTreeModel(0, 0)
    property var sequence: tester.getSequenceModel(1)
    property var noSequence: tester.getSequenceModel(0) || null
    property var noTree: tester.getTreeModel(-1, 0) || null
    property bool missingIsNull: noSequence === null
    Component.onCompleted: tree.setData(tree.index(0, 0), "hello")
    property int editorRows: editor.rows
    property bool editorVisible: editor.visible
    TreeView {
        id: editor
        anchors.fill: parent
        model: tree
        visible: tree !== null && noSequence === null
    }
}''', QUrl())
        obj = component.create()
        self.assertIsNotNone(obj, str(component.errors()))
        self.assertIs(obj.property("tree"), model.getTreeModel(0, 0))
        self.assertIs(obj.property("sequence"), model.getSequenceModel(1))
        self.assertIsNone(obj.property("noSequence"))
        self.assertIsNone(obj.property("noTree"))
        app.processEvents()
        self.assertTrue(obj.property("missingIsNull"))
        self.assertTrue(obj.property("editorVisible"))
        self.assertEqual(obj.property("editorRows"), 1)
        tree = model.getTreeModel(0, 0)
        self.assertEqual(tree.getStrValue(tree.index(0, 0)), "hello")
        self.assertEqual(tree.rootItem.dataType.value, "hello")
        meta = model.metaObject()
        for signature in ("getTreeModel(int,int)", "getSequenceModel(int)"):
            self.assertEqual(meta.method(meta.indexOfMethod(signature)).typeName(), "QVariant")
        obj.deleteLater()
        app.processEvents()


if __name__ == "__main__":
    unittest.main()
