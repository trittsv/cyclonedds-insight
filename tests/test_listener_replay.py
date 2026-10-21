"""
 * Copyright(c) 2026 Sven Trittler
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
"""

import json
import tempfile
import time
import unittest
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QCoreApplication, QObject, QStandardPaths, QTimer, Signal, Slot
from cyclonedds.idl import IdlEnum, IdlStruct
from cyclonedds.idl.types import array, int32, sequence
from loguru import logger

from models.data_tree_model import DataTreeModel
from models.listener.listener_model import ListenerModel
from models.listener.receiver_model import ReceiverModel
from models.listener.replay_model import ReplayModel, ReplaySession
from models.listener.sample_tree_model import SampleTreeModel
from models.tester_model import SequenceItem, TesterModel, WriterItem
from module_handler import DataModelHandler


class Mode(IdlEnum, typename="ReplayTests::Mode"):
    OFF = 0
    ON = 1


@dataclass
class Child(IdlStruct, typename="ReplayTests::Child"):
    name: str
    number: int32


@dataclass
class Sample(IdlStruct, typename="ReplayTests::Sample"):
    number: int32
    children: sequence[Child]
    numbers: sequence[int32]
    fixed: array[int32, 2]
    optional: Optional[int32]
    mode: Mode


@dataclass
class Nested(IdlStruct, typename="ReplayTests::Nested"):
    child: Optional[Child]
    arrays: sequence[sequence[int32]]
    fixed_children: array[Child, 2]


def sample(number=1, optional=None):
    return Sample(number, [Child("nested", 7)], [3, 4], [5, 6], optional, Mode.ON)


def wait_until(predicate, timeout=2):
    deadline = time.monotonic() + timeout
    while not predicate() and time.monotonic() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.001)
    assert predicate(), "Timed out waiting for Qt events"


class Worker(QObject):
    replayWritten = Signal(str, bool, str)

    def __init__(self):
        super().__init__()
        self.writers = set()
        self.sent = []

    @Slot(str, object)
    def writeReplay(self, writer_id, obj):
        if writer_id in self.writers:
            self.sent.append((obj.number, time.monotonic(), obj.serialize()))
            self.replayWritten.emit(writer_id, True, "")

    def deleteReplayWriter(self, writer_id):
        self.writers.discard(writer_id)


class Repository(QObject):
    newWriterSignal = Signal(str, int, str, str, object)
    endpointFailed = Signal(str, str)
    operationError = Signal(str)

    def __init__(self, handler):
        super().__init__()
        self.dataModelHandler = handler
        self.threads = {0: Worker()}
        self.requests = []

    def createEndpointFromTester(self, writer_id, domain, topic, typename, entity, name, root, qos):
        self.requests.append((writer_id, domain, topic, typename, qos))

        def ready():
            self.threads[domain].writers.add(writer_id)
            self.newWriterSignal.emit(writer_id, domain, topic, typename, qos)
        QTimer.singleShot(0, ready)


class ListenerReplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])
        QStandardPaths.setTestModeEnabled(True)
        logger.remove()

    def setUp(self):
        self.handler = DataModelHandler()
        self.handler.addTypeFromNetwork(Sample.__idl_typename__, Sample)
        self.repository = Repository(self.handler)
        self.listener = ListenerModel({})
        self.listener.addReader("reader", 0, "first", Sample.__idl_typename__, {"topic_qos": {}})
        self.receiver = ReceiverModel(self.handler, self.listener)
        self.errors = []
        self.receiver.operationError.connect(self.errors.append)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def record(self):
        base = time.monotonic_ns()
        for index, topic in enumerate(("first", "second", "first")):
            self.listener.readers["reader"].topic_name = topic
            obj = sample(index + 1, 42 if index == 1 else None)
            self.receiver.addReceivedMsg(
                "reader", str(obj), "info", True, "source", "delay", "received",
                "writer", "reader-guid", "app", "host", "pid", "addresses",
                Sample.__idl_typename__, topic, "handle",
                {"sample": obj, "received_monotonic_ns": base + index * 20_000_000})
        path = Path(self.tmp.name) / "recording.json"
        self.receiver.exportReplay(str(path))
        self.assertEqual(self.errors, [])
        return path, json.loads(path.read_text())

    def test_shared_preset_serialization_roundtrip(self):
        for optional in (None, 42):
            original = sample(optional=optional)
            tree = DataTreeModel(self.handler.getRootNode(Sample.__idl_typename__))
            tree.fromDataObject(original, self.handler)
            restored = DataTreeModel(self.handler.getRootNode(Sample.__idl_typename__))
            restored.fromJson(tree.toJson()["root"], self.handler)
            self.assertEqual(restored.getDataObj().serialize(), original.serialize())
            self.assertEqual(len(restored.getDataObj().fixed), 2)

    def test_nested_containers_and_optional_struct_roundtrip(self):
        self.handler.addTypeFromNetwork(Nested.__idl_typename__, Nested)
        original = Nested(Child("optional", 9), [[1, 2], [], [3]], [Child("a", 1), Child("b", 2)])
        tree = DataTreeModel(self.handler.getRootNode(Nested.__idl_typename__))
        tree.fromDataObject(original, self.handler)
        restored = DataTreeModel(self.handler.getRootNode(Nested.__idl_typename__))
        restored.fromJson(tree.toJson()["root"], self.handler)
        self.assertEqual(restored.getDataObj().serialize(), original.serialize())

    def test_legacy_optional_scalar_presets(self):
        tree = DataTreeModel(self.handler.getRootNode(Sample.__idl_typename__))
        tree.fromJson({"optional": 42}, self.handler)
        restored = DataTreeModel(self.handler.getRootNode(Sample.__idl_typename__))
        restored.fromJson(tree.toJson()["root"], self.handler)
        self.assertEqual(restored.getDataObj().optional, 42)

    def test_recording_imports_as_tester_presets(self):
        path, document = self.record()
        self.assertEqual(len(document["presets"]), 2)
        self.assertEqual([e["offset_ms"] for e in document["replay"]["events"]], [0, 20, 40])
        tester = TesterModel({}, self.handler, self.repository)
        tester.operationError.connect(self.errors.append)
        tester.importJson(str(path))
        self.assertEqual(self.errors, [])
        self.assertEqual(len(tester.items), 3)
        writers = [item for item in tester.items.values() if isinstance(item, WriterItem)]
        sequence = next(item for item in tester.items.values() if isinstance(item, SequenceItem))
        self.assertEqual(sequence.sequenceItems, [e["message_id"] for e in document["replay"]["events"]])
        self.assertEqual([len(item.getDataTreeModels()) for item in writers], [2, 1])
        for item in writers:
            self.assertEqual(item.qos, {"topic_qos": {}})

    def test_listener_history_is_automatically_available_until_clear(self):
        path, _ = self.record()
        self.assertEqual(self.receiver.replayCount, 3)
        self.receiver.instanceView = True
        self.receiver.exportReplay(str(path))
        self.assertEqual(len(json.loads(path.read_text())["replay"]["events"]), 3)
        self.receiver.clear()
        self.assertEqual(self.receiver.replayCount, 0)
        self.assertEqual(self.receiver.rowCount(), 0)
        self.receiver.exportReplay(str(path))
        self.assertTrue(self.errors)

    def test_recording_sorts_cross_reader_delivery(self):
        path, _ = self.record()
        self.receiver._messages.reverse()
        self.receiver.exportReplay(str(path))
        document = json.loads(path.read_text())
        self.assertEqual([e["offset_ms"] for e in document["replay"]["events"]], [0, 20, 40])
        session = ReplaySession(str(path), document, self.repository)
        self.assertEqual([event["tree"].getDataObj().number for event in session.events], [1, 2, 3])

    def test_replay_order_and_original_timing(self):
        path, document = self.record()
        session = ReplaySession(str(path), document, self.repository)
        session.operationError.connect(self.errors.append)
        session.play(0, 2, True, 100)
        wait_until(lambda: not session.playing)
        sent = self.repository.threads[0].sent
        self.assertEqual([row[0] for row in sent], [1, 2, 3])
        self.assertGreaterEqual(sent[2][1] - sent[0][1], 0.035)
        self.assertLess(sent[2][1] - sent[0][1], 0.5)
        self.assertEqual(sent[1][2], sample(2, 42).serialize())
        self.assertEqual(self.errors, [])
        self.assertFalse(self.repository.threads[0].writers)

    def test_partial_replay_fixed_timing_and_stop(self):
        path, document = self.record()
        session = ReplaySession(str(path), document, self.repository)
        session.play(1, 2, False, 100)
        wait_until(lambda: not session.playing)
        sent = self.repository.threads[0].sent
        self.assertEqual([row[0] for row in sent], [2, 3])
        self.assertGreaterEqual(sent[1][1] - sent[0][1], 0.09)
        session.play(0, 2, False, 100)
        session.stop()  # Endpoint creation is still in flight.
        wait_until(lambda: not session.cancelled)
        self.assertEqual(len(sent), 2)
        self.assertFalse(self.repository.threads[0].writers)

    def test_individually_selected_messages_use_fixed_interval(self):
        path, document = self.record()
        session = ReplaySession(str(path), document, self.repository)
        session.operationError.connect(self.errors.append)
        self.assertEqual(session.selectedRows, [0, 1, 2])
        session.setSelected(1, False)
        self.assertEqual(session.selectedRows, [0, 2])
        session.playSelected(False, 100)
        session.selectAll(False)  # Selection remains stable during playback.
        self.assertEqual(session.selectedRows, [0, 2])
        wait_until(lambda: not session.playing)
        sent = self.repository.threads[0].sent
        self.assertEqual([row[0] for row in sent], [1, 3])
        self.assertGreaterEqual(sent[1][1] - sent[0][1], 0.09)
        self.assertEqual(self.errors, [])

    def test_selected_messages_preserve_original_time_gaps(self):
        path, document = self.record()
        session = ReplaySession(str(path), document, self.repository)
        session.setSelected(1, False)
        session.playSelected(True, 100)
        wait_until(lambda: not session.playing)
        sent = self.repository.threads[0].sent
        self.assertEqual([row[0] for row in sent], [1, 3])
        self.assertGreaterEqual(sent[1][1] - sent[0][1], 0.035)
        self.assertLess(sent[1][1] - sent[0][1], 0.5)
        session.selectAll(False)
        session.operationError.connect(self.errors.append)
        session.playSelected(False, 100)
        self.assertFalse(session.playing)
        self.assertEqual(len(sent), 2)
        self.assertTrue(self.errors)
        session.selectAll(True)
        self.assertEqual(session.selectedRows, [0, 1, 2])

    def test_invalid_replay_import_is_atomic(self):
        path, document = self.record()
        document["replay"]["events"][1]["message_id"] = "missing"
        path.write_text(json.dumps(document))
        manager = ReplayModel(self.repository)
        manager.operationError.connect(self.errors.append)
        self.assertFalse(manager.importJson(str(path)))
        self.assertEqual(manager.sessions, [])
        self.assertTrue(self.errors)
        self.assertFalse(self.repository.requests)

    def test_watches_survive_collapse_and_can_be_cleared(self):
        tree = SampleTreeModel()
        tree.watchStore = self.receiver
        tree.scope = "reader"
        tree.payload = {"root": {"nested": {"value": 42}, "other": 3}}
        tree.toggle(1)  # Expand nested.
        value_row = next(i for i, row in enumerate(tree._rows) if row["fieldLabel"] == "value")
        tree.toggleWatch(value_row)
        tree.toggle(0)  # Collapse root.
        self.assertEqual([row["fieldValue"] for row in tree._rows], ["{2}", "42"])
        self.receiver.clearWatchlist()
        self.assertEqual(tree.count, 1)

    def test_parent_watch_highlights_each_descendant_after_collapse(self):
        tree = SampleTreeModel()
        tree.watchStore = self.receiver
        tree.scope = "reader"
        tree.payload = {"root": {"nested": {"a": 1, "deeper": {"b": 2}, "list": [3, 4]}, "other": 5}}
        tree.toggleWatch(1)  # Watch the entire nested object.
        tree.toggle(0)  # Collapse root.
        watched = [row for row in tree._rows if row["watched"]]
        self.assertEqual([row["fieldValue"] for row in watched if not row["expandable"]],
                         ["1", "2", "3", "4"])
        self.assertNotIn("5", [row["fieldValue"] for row in watched])
        self.assertTrue(all(row["depth"] == 0 for row in watched))
        # A later sample's new fields inherit the parent watch as well.
        tree.payload = {"root": {"nested": {"a": 1, "new": 6}, "other": 5}}
        self.assertTrue(next(row for row in tree._rows if row["fieldValue"] == "6")["watched"])
        value_row = next(i for i, row in enumerate(tree._rows) if row["fieldValue"] == "1")
        tree.toggleWatch(value_row)  # Remove one inherited field, preserving siblings.
        self.assertNotIn("1", [row["fieldValue"] for row in tree._rows])
        self.assertTrue(next(row for row in tree._rows if row["fieldValue"] == "6")["watched"])
        self.receiver.clearWatchlist()
        self.assertEqual(tree.count, 1)
        self.assertFalse(self.receiver.watchExclusions)


if __name__ == "__main__":
    unittest.main()
