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

import copy
import json
import math
import time
import uuid
from pathlib import Path

from PySide6.QtCore import qtTrId, QObject, Property, QTimer, Qt, Signal, Slot
from models.data_tree_model import DataTreeModel
from loguru import logger as logging


class ReplaySession(QObject):
    changed = Signal()
    selectionChanged = Signal()
    operationError = Signal(str)
    writeSignal = Signal(str, object)

    def __init__(self, filePath, document, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self._name = Path(filePath).name
        self.events = []
        self.presets = {}
        self.trees = []
        self.writers = {}
        self.pending = set()
        self.connectedThreads = set()
        self._playing = False
        self._position = 0
        self._playback = []
        self._cursor = 0
        self._original = False
        self._interval = 100
        self._waiting = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self._send)
        self.startupTimer = QTimer(self)
        self.startupTimer.setSingleShot(True)
        self.startupTimer.setInterval(30000)
        self.startupTimer.timeout.connect(lambda: self._fail(qtTrId("listener.error.timeout")))
        try:
            self._load(document)
        except Exception:
            self.deleteLater()
            raise
        self._selected = set(range(len(self.events)))
        self.repository.newWriterSignal.connect(self._writerReady)
        self.repository.endpointFailed.connect(self._writerFailed)

    def _load(self, document):
        if not isinstance(document, dict) or not isinstance(document.get("presets"), list):
            raise ValueError(qtTrId("listener.error.format"))
        messages = {}
        fallback = []
        for preset in document["presets"]:
            if not isinstance(preset, dict):
                raise ValueError(qtTrId("listener.error.preset"))
            preset = copy.deepcopy(preset)
            preset_id = preset.setdefault("id", str(uuid.uuid4()))
            if not isinstance(preset_id, str) or preset_id in self.presets:
                raise ValueError(qtTrId("listener.error.preset.id"))
            if (not isinstance(preset.get("domain_id", 0), int)
                    or not 0 <= preset.get("domain_id", 0) <= 232
                    or not isinstance(preset.get("qos", {}), dict)
                    or not isinstance(preset.get("topic_name"), str)
                    or not preset["topic_name"] or not isinstance(preset.get("topic_type"), str)):
                raise ValueError(qtTrId("listener.error.metadata"))
            self.presets[preset_id] = preset
            additional = preset.get("messages", [])
            if not isinstance(additional, list):
                raise ValueError(qtTrId("listener.error.messages"))
            for message in [preset.get("message")] + additional:
                if not isinstance(message, dict) or not isinstance(message.get("root"), dict):
                    raise ValueError(qtTrId("listener.error.message"))
                message_id = message.setdefault("id", str(uuid.uuid4()))
                key = (preset_id, message_id)
                if not isinstance(message_id, str) or key in messages:
                    raise ValueError(qtTrId("listener.error.message.id"))
                missing = set()
                root = self.repository.dataModelHandler.getRootNode(preset["topic_type"], missing)
                if missing:
                    raise ValueError(qtTrId("listener.error.types").replace("%1", ", ".join(sorted(missing))))
                tree = DataTreeModel(root, self)
                self.trees.append(tree)
                tree.fromJson(message["root"], self.repository.dataModelHandler)
                messages[key] = (tree, message)
                fallback.append({"preset_id": preset_id, "message_id": message_id,
                                 "offset_ms": len(fallback) * 100})
        replay = document.get("replay", {})
        if not isinstance(replay, dict) or replay.get("version", 1) != 1:
            raise ValueError(qtTrId("listener.error.version"))
        events = replay.get("events", fallback)
        if not isinstance(events, list) or not events:
            raise ValueError(qtTrId("listener.error.empty"))
        previous = -1
        for event in events:
            if not isinstance(event, dict):
                raise ValueError(qtTrId("listener.error.event"))
            key = (event.get("preset_id"), event.get("message_id"))
            if key not in messages:
                raise ValueError(qtTrId("listener.error.reference"))
            offset = event.get("offset_ms", previous + 100)
            if not isinstance(offset, (int, float)) or not math.isfinite(offset) or offset < max(0, previous):
                raise ValueError(qtTrId("listener.error.timestamps"))
            previous = offset
            tree, message = messages[key]
            self.events.append({"preset_id": key[0], "tree": tree, "offset_ms": offset,
                                "topic": self.presets[key[0]]["topic_name"],
                                "text": str(tree.getDataObj()), "structured": message})

    @Property(str, constant=True)
    def name(self):
        return self._name

    @Property(list, constant=True)
    def rows(self):
        return [{"topic": e["topic"], "text": e["text"], "offset_ms": e["offset_ms"]}
                for e in self.events]

    @Property(bool, notify=changed)
    def playing(self):
        return self._playing

    @Property(int, notify=changed)
    def position(self):
        return self._position

    @Property(list, notify=selectionChanged)
    def selectedRows(self):
        return sorted(self._selected)

    @Slot(int, bool)
    def setSelected(self, row, selected):
        if self._playing or not 0 <= row < len(self.events):
            return
        if selected:
            self._selected.add(row)
        else:
            self._selected.discard(row)
        self.selectionChanged.emit()

    @Slot(bool)
    def selectAll(self, selected):
        if self._playing:
            return
        self._selected = set(range(len(self.events))) if selected else set()
        self.selectionChanged.emit()

    @Slot(bool, int)
    def playSelected(self, original, interval):
        self._startPlayback(self.selectedRows, original, interval)

    @Slot(int, int, bool, int)
    def play(self, first, last, original, interval):
        self._startPlayback(list(range(first, last + 1)), original, interval)

    def _startPlayback(self, rows, original, interval):
        self.stop()
        if not rows or any(not 0 <= row < len(self.events) for row in rows) or not 1 <= interval <= 60000:
            self.operationError.emit(qtTrId("listener.error.range"))
            return
        self._playback = rows
        self._cursor = 0
        self._position = rows[0]
        self._original, self._interval = original, interval
        self._playing = True
        required = {self.events[row]["preset_id"] for row in rows}
        self.writers = {
            preset_id: f"replay-{self.presets[preset_id].get('domain_id', 0)}-{uuid.uuid4()}"
            for preset_id in required
        }
        self.pending = set(self.writers.values())
        self.changed.emit()
        self.startupTimer.start()
        for preset_id, writer_id in list(self.writers.items()):
            if not self._playing:
                break
            preset = self.presets[preset_id]
            try:
                self.repository.createEndpointFromTester(
                    writer_id, preset.get("domain_id", 0), preset["topic_name"],
                    preset["topic_type"], 4, self._name, {}, copy.deepcopy(preset.get("qos", {})))
            except Exception as error:
                self._fail(str(error))

    @Slot(str, int, str, str, object)
    def _writerReady(self, writer_id, domain, topic, typename, qos):
        if writer_id not in self.pending:
            # A stopped replay may still have an asynchronous creation in flight.
            if writer_id in getattr(self, "cancelled", set()):
                self.repository.threads[domain].deleteReplayWriter(writer_id)
                self.cancelled.discard(writer_id)
            return
        thread = self.repository.threads[domain]
        if thread not in self.connectedThreads:
            self.writeSignal.connect(thread.writeReplay, Qt.QueuedConnection)
            thread.replayWritten.connect(self._written, Qt.QueuedConnection)
            self.connectedThreads.add(thread)
        self.pending.remove(writer_id)
        if not self.pending:
            self.startupTimer.stop()
            self._due = time.monotonic()
            self.timer.start(0)

    @Slot(str, str)
    def _writerFailed(self, writer_id, message):
        getattr(self, "cancelled", set()).discard(writer_id)
        if writer_id in self.pending:
            self._fail(message)

    def _send(self):
        if not self._playing or self.pending:
            return
        remaining = math.ceil((self._due - time.monotonic()) * 1000)
        if remaining > 0:
            self.timer.start(min(remaining, 2147483647))
            return
        event = self.events[self._position]
        self._waiting = True
        self.startupTimer.start()
        self.writeSignal.emit(self.writers[event["preset_id"]], copy.deepcopy(event["tree"].getDataObj()))

    @Slot(str, bool, str)
    def _written(self, writer_id, success, error):
        if not self._playing or not self._waiting or writer_id not in self.writers.values():
            return
        self._waiting = False
        self.startupTimer.stop()
        if not success:
            self._fail(error)
            return
        if self._cursor == len(self._playback) - 1:
            self.stop()
            return
        next_position = self._playback[self._cursor + 1]
        gap = (self.events[next_position]["offset_ms"] - self.events[self._position]["offset_ms"]
               if self._original else self._interval)
        self._cursor += 1
        self._position = next_position
        self._due += gap / 1000
        self.changed.emit()
        self.timer.start(0)

    def _fail(self, error):
        self.stop()
        logging.error(qtTrId("listener.error.replay").replace("%1", str(error)))
        self.operationError.emit(qtTrId("listener.error.replay").replace("%1", str(error)))

    @Slot()
    def stop(self):
        self.timer.stop()
        self.startupTimer.stop()
        self.cancelled = getattr(self, "cancelled", set()) | self.pending
        for thread in self.repository.threads.values():
            for writer_id in self.writers.values():
                thread.deleteReplayWriter(writer_id)
        self.pending.clear()
        self.writers.clear()
        self._waiting = False
        self._playing = False
        self.changed.emit()


class ReplayModel(QObject):
    sessionsChanged = Signal()
    operationError = Signal(str)

    def __init__(self, repository, parent=None):
        super().__init__(parent)
        self.repository = repository
        self._sessions = []
        self._cancelledWriters = set()
        repository.newWriterSignal.connect(self._cleanupWriter)
        repository.endpointFailed.connect(self._cleanupFailedWriter)

    @Property(list, notify=sessionsChanged)
    def sessions(self):
        return self._sessions

    @Slot(str, result=bool)
    def importJson(self, filePath):
        try:
            with open(filePath, encoding="utf-8") as file:
                document = json.load(file)
            session = ReplaySession(filePath, document, self.repository, self)
            session.operationError.connect(self.operationError.emit)
            self._sessions.append(session)
            self.sessionsChanged.emit()
            return True
        except Exception as error:
            logging.error(qtTrId("listener.error.import").replace("%1", str(error)))
            self.operationError.emit(qtTrId("listener.error.import").replace("%1", str(error)))
            return False

    @Slot(int)
    def close(self, index):
        if 0 <= index < len(self._sessions):
            session = self._sessions.pop(index)
            session.stop()
            self._cancelledWriters.update(session.cancelled)
            self.repository.newWriterSignal.disconnect(session._writerReady)
            self.repository.endpointFailed.disconnect(session._writerFailed)
            self.sessionsChanged.emit()
            session.deleteLater()

    @Slot()
    def stopAll(self):
        for session in self.findChildren(ReplaySession):
            session.stop()

    @Slot(str, int, str, str, object)
    def _cleanupWriter(self, writer_id, domain, topic, typename, qos):
        if writer_id in self._cancelledWriters:
            self.repository.threads[domain].deleteReplayWriter(writer_id)
            self._cancelledWriters.discard(writer_id)

    @Slot(str, str)
    def _cleanupFailedWriter(self, writer_id, message):
        self._cancelledWriters.discard(writer_id)
