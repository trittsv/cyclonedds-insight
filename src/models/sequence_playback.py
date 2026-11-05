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
import math
import time

from PySide6.QtCore import QObject, Property, QTimer, Qt, Signal, Slot, qtTrId
from loguru import logger as logging
from utils.sequence_utils import sequence_steps


class SequenceSender(QObject):
    write = Signal(str, object)
    dispose = Signal(str, object)


class SequencePlayback(QObject):
    changed = Signal()
    operationError = Signal(str)

    def __init__(self, tester):
        super().__init__(tester)
        self.tester = tester
        self._sequence = None
        self._playing = False
        self._repeat = False
        self._waiting = False
        self._pending = set()
        self._entries = []
        self._cursor = 0
        self._completed = 0
        self._inflight = None
        self._senders = {}
        self._closed = False
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setTimerType(Qt.PreciseTimer)
        self.timer.timeout.connect(self._send)
        self.timeout = QTimer(self)
        self.timeout.setSingleShot(True)
        self.timeout.setInterval(30000)
        self.timeout.timeout.connect(lambda: self._fail(qtTrId("listener.error.timeout")))
        tester.datamodelRepoModel.newWriterSignal.connect(self._writerReady)
        tester.datamodelRepoModel.endpointFailed.connect(self._writerFailed)

    @Property(bool, notify=changed)
    def playing(self):
        return self._playing

    @Property(bool, notify=changed)
    def busy(self):
        return self._playing or self._waiting or bool(self._pending)

    @Property(bool, notify=changed)
    def preparing(self):
        return bool(self._pending)

    @Property(QObject, notify=changed)
    def sequence(self):
        return self._sequence

    @Property(int, notify=changed)
    def position(self):
        return self._entries[self._cursor]["row"] if self._entries else -1

    @Property(int, notify=changed)
    def completed(self):
        return self._completed

    @Property(int, notify=changed)
    def total(self):
        return len(self._entries)

    def start(self, sequence, rows, use_delays, interval, repeat=False):
        if self.busy or self._closed:
            return
        try:
            steps = sequence_steps({"sequence_steps": sequence.sequenceSteps})
            rows = sorted(set(rows))
            if not rows or any(not 0 <= row < len(steps) for row in rows) or not 1 <= interval <= 60000:
                raise ValueError(qtTrId("listener.error.range"))
            selected = set(rows)
            entries = []
            offset = 0
            for row, step in enumerate(steps):
                offset += step["delay_ms"]
                if row not in selected:
                    continue
                writer_id, data_index = self.tester._getDataReference(step["message_id"])
                writer = self.tester.items.get(writer_id)
                if writer is None:
                    raise ValueError(qtTrId("listener.error.reference"))
                entries.append({"row": row, "offset_ms": offset, "writer_id": writer_id,
                                "domain": writer.getDomainId(), "operation": step["operation"],
                                "topic_type": writer.getTopicType(),
                                "root": writer.messageSnapshot(data_index)["root"]})
        except Exception as error:
            self.operationError.emit(str(error))
            return
        self._entries = entries
        self._sequence = sequence
        self._cursor = self._completed = 0
        self._use_delays, self._interval = use_delays, interval
        self._repeat = repeat
        self._cycle_duration_ms = offset
        self._playing = True
        self._pending = {entry["writer_id"] for entry in entries
                         if not self.tester.items[entry["writer_id"]].getIsStarted()}
        self.changed.emit()
        if self._pending:
            self.timeout.start()
            for writer_id in list(self._pending):
                self.tester._startWriter(writer_id)
        else:
            self._begin()

    def _begin(self):
        if not self._playing or self._closed:
            self.changed.emit()
            return
        try:
            for entry in self._entries:
                worker = self.tester.threads[entry["domain"]]
                if worker not in self._senders:
                    sender = SequenceSender(self)
                    sender.write.connect(worker.writeSequence, Qt.QueuedConnection)
                    sender.dispose.connect(worker.disposeSequence, Qt.QueuedConnection)
                    worker.sequenceWritten.connect(self._written, Qt.QueuedConnection)
                    self._senders[worker] = sender
            self._due = time.monotonic()
            self.timer.start(0)
        except Exception as error:
            self._fail(str(error))
        self.changed.emit()

    @Slot(str, int, str, str, object)
    def _writerReady(self, writer_id, domain, topic, typename, qos):
        if writer_id not in self._pending:
            return
        self._pending.remove(writer_id)
        if not self._pending:
            self.timeout.stop()
            self._begin()
        else:
            self.changed.emit()

    @Slot(str, str)
    def _writerFailed(self, writer_id, error):
        if writer_id in self._pending:
            self._fail(error)

    def _send(self):
        if not self._playing or self._pending or self._waiting:
            return
        remaining = math.ceil((self._due - time.monotonic()) * 1000)
        if remaining > 0:
            self.timer.start(min(remaining, 2147483647))
            return
        entry = self._entries[self._cursor]
        tree = None
        try:
            # Materialize only the current message on its owning UI thread.
            # The temporary tree is released after conversion, not cached for
            # every message in a large recording.
            tree = self.tester._createDataTreeModel(entry["topic_type"], entry["root"])
            data = copy.deepcopy(tree.getDataObj())
        except Exception as error:
            self._fail(str(error))
            return
        finally:
            if tree is not None:
                tree.deleteLater()
        self._waiting = True
        self._inflight = entry["writer_id"]
        self.timeout.start()
        sender = self._senders[self.tester.threads[entry["domain"]]]
        signal = sender.dispose if entry["operation"] == "dispose" else sender.write
        signal.emit(self._inflight, data)

    @Slot(str, bool, str)
    def _written(self, writer_id, success, error):
        if not self._waiting or writer_id != self._inflight:
            return
        self._waiting = False
        self._inflight = None
        self.timeout.stop()
        if not success:
            self._fail(error)
            return
        self._completed += 1
        if not self._playing:
            self.stop()
            return
        previous = self._entries[self._cursor]
        if self._cursor == len(self._entries) - 1:
            if not self._repeat:
                self.stop()
                return
            self._cursor = self._completed = 0
            # Keep omitted leading/trailing delays when the selection wraps.
            gap = (self._cycle_duration_ms - previous["offset_ms"] + self._entries[0]["offset_ms"]
                   if self._use_delays else self._interval)
        else:
            self._cursor += 1
            current = self._entries[self._cursor]
            gap = current["offset_ms"] - previous["offset_ms"] if self._use_delays else self._interval
        self._due += gap / 1000
        self.changed.emit()
        self.timer.start(0)

    @Slot()
    def stop(self):
        self.timer.stop()
        self._playing = False
        for entry in self._entries:
            entry.pop("root", None)
        # Keep an in-flight operation and pending creations tracked. Editing or
        # restarting is safe only after their acknowledgements have arrived.
        self.changed.emit()

    def _fail(self, error):
        self.timer.stop()
        self.timeout.stop()
        self._playing = False
        self._pending.clear()
        for entry in self._entries:
            entry.pop("root", None)
        self.changed.emit()
        message = qtTrId("tester.sequence.error").replace("%1", str(error))
        logging.error(message)
        self.operationError.emit(message)

    def clear(self):
        if self.busy:
            return
        self._sequence = None
        self._entries.clear()
        self._completed = 0
        self.changed.emit()

    @Slot()
    def shutdown(self):
        self._closed = True
        self.stop()
        self.timeout.stop()
