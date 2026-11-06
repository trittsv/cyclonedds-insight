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

"""Worker-owned preset file I/O; all QObject models remain on the UI thread."""

import json
import time
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, Property, QIODevice, QSaveFile, QThread, Signal, Slot, qtTrId
from loguru import logger as logging
from utils.sequence_utils import sequence_steps


class PresetJob(QThread):
    advanced = Signal(float)

    def __init__(self, function, parent):
        super().__init__(parent)
        self.function = function
        self.result = None
        self.error = None
        self.last_progress = 0

    def check(self):
        if self.isInterruptionRequested():
            raise InterruptedError("Preset operation interrupted")

    def progress(self, value):
        self.check()
        now = time.monotonic()
        if now - self.last_progress >= 0.05 or value >= 1:
            self.last_progress = now
            self.advanced.emit(value)

    def run(self):
        try:
            self.result = self.function(self.progress, self.check)
        except Exception as error:
            self.error = str(error)
        finally:
            self.function = None


class PresetIo(QObject):
    changed = Signal()
    failed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._job = None
        self._operation = ""
        self._progress = -1.0
        self._closed = False
        self._callback = None
        self.allowed = lambda: True

    @Property(bool, notify=changed)
    def busy(self):
        return self._job is not None

    @Property(str, notify=changed)
    def operation(self):
        return self._operation

    @Property(float, notify=changed)
    def progress(self):
        return self._progress

    def start(self, operation, function, callback):
        if self.busy or self._closed or not self.allowed():
            return False
        self._operation, self._progress = operation, -1.0
        self._callback = callback
        self._job = PresetJob(function, self)
        self._job.advanced.connect(self._advanced)
        self._job.finished.connect(self._finished)
        self.changed.emit()
        self._job.start()
        return True

    @Slot(float)
    def _advanced(self, value):
        if self._job is not None:
            self._progress = max(self._progress, max(0.0, min(1.0, value)))
            self.changed.emit()

    @Slot()
    def _finished(self):
        job = self._job
        callback = self._callback
        self._job = self._callback = None
        self._progress = -1.0
        try:
            if not self._closed:
                callback(job.result, job.error)
        except Exception as error:
            logging.exception("Failed to finish preset operation")
            self.failed.emit(str(error))
        finally:
            job.result = None
            job.deleteLater()
            self.changed.emit()

    @Slot()
    def shutdown(self):
        self._closed = True
        if self._job is not None:
            self._job.requestInterruption()
            self._job.wait()


class JsonArray(list):
    """An encoder-compatible array whose elements are generated as they are written."""
    def __init__(self, count, values):
        super().__init__()
        self.count, self.values = count, values

    def __len__(self):
        return self.count

    def __iter__(self):
        return iter(self.values())


def save_json(path, document, check):
    output = QSaveFile(str(path))
    if not output.open(QIODevice.WriteOnly):
        raise OSError(output.errorString())
    try:
        parts, size = [], 0
        for part in json.JSONEncoder(indent=4).iterencode(document):
            parts.append(part)
            size += len(part)
            if size >= 65536:
                check()
                content = "".join(parts).encode("utf-8")
                if output.write(content) != len(content):
                    raise OSError(output.errorString())
                parts, size = [], 0
        check()
        if parts:
            content = "".join(parts).encode("utf-8")
            if output.write(content) != len(content):
                raise OSError(output.errorString())
        if not output.commit():
            raise OSError(output.errorString())
    except Exception:
        output.cancelWriting()
        raise


def load_presets(paths, recording, used_ids, available, progress, check):
    """Validate/remap plain data on the worker; return descriptors for UI publication."""
    available = set(available)
    used_ids = set(used_ids) | available
    total_bytes = sum(Path(path).stat().st_size for path in paths) or 1
    bytes_done = 0
    writers, sequences = [], []
    for path in paths:
        check()
        size = Path(path).stat().st_size
        with open(path, encoding="utf-8") as file:
            document = json.load(file)
        check()
        bytes_done += size
        progress(0.6 * bytes_done / total_bytes)
        if not isinstance(document, dict) or "replay" in document:
            raise ValueError(qtTrId("listener.error.format"))
        presets, sequence_presets = document.get("presets", []), document.get("sequence_presets", [])
        if not isinstance(presets, list) or not isinstance(sequence_presets, list):
            raise ValueError(qtTrId("listener.error.format"))
        references, imported = {}, []
        for preset in presets:
            check()
            source_id = preset.get("id", str(uuid.uuid4()))
            if not isinstance(source_id, str) or not source_id or source_id in references:
                raise ValueError(qtTrId("listener.error.preset.id"))
            writer_id = str(uuid.uuid4()) if source_id in used_ids else source_id
            used_ids.add(writer_id)
            references[source_id] = writer_id
            domain, topic, typename, qos = (preset.get("domain_id", 0), preset.get("topic_name"),
                                          preset.get("topic_type"), preset.get("qos", {}))
            if (isinstance(domain, bool) or not isinstance(domain, int) or not 0 <= domain <= 232
                    or not isinstance(topic, str) or not topic or not isinstance(typename, str) or not typename
                    or not isinstance(qos, dict)):
                raise ValueError(qtTrId("listener.error.metadata"))
            additional = preset.pop("messages", [])
            messages = [preset.pop("message", {"root": {}})] + additional
            ids, names, index_by_id = [], [], {}
            for index, message in enumerate(messages):
                if index % 1000 == 0:
                    check()
                    progress(0.6 + 0.15 * bytes_done / total_bytes)
                if not isinstance(message, dict) or not isinstance(message.get("root"), dict):
                    raise ValueError(qtTrId("listener.error.message"))
                old_id = message.get("id") or (source_id if index == 0 else str(uuid.uuid4()))
                if (not isinstance(old_id, str) or not old_id or
                        (old_id in references and (index != 0 or old_id != source_id))):
                    raise ValueError(qtTrId("listener.error.message.id"))
                message_id = writer_id if index == 0 else (str(uuid.uuid4()) if old_id in used_ids else old_id)
                used_ids.add(message_id)
                references[old_id] = message_id
                message["id"] = message_id
                ids.append(message_id)
                names.append(str(message.get("name") or "").strip() or f"Data {index + 1}")
                index_by_id[message_id] = index
                imported.append(message_id)
            preset.update(id=writer_id, domain_id=domain, topic_name=topic, topic_type=typename,
                          qos=qos, messages=messages, ids=ids, names=names, index_by_id=index_by_id)
            writers.append(preset)
        available.update(imported)
        if recording and not sequence_presets and imported:
            sequence_presets = [{"preset_name": Path(path).stem, "sequence_items": imported}]
        for sequence in sequence_presets:
            # The worker owns these dictionaries; no extra full-size deepcopy is needed.
            steps = sequence_steps(sequence, copy_steps=False)
            for index, step in enumerate(steps):
                if index % 1000 == 0:
                    check()
                    progress(0.75 + 0.2 * bytes_done / total_bytes)
                step["message_id"] = references.get(step["message_id"], step["message_id"])
                if step["message_id"] not in available:
                    raise ValueError(qtTrId("listener.error.reference"))
            source_id = sequence.get("id", str(uuid.uuid4()))
            if not isinstance(source_id, str) or not source_id:
                raise ValueError(qtTrId("listener.error.preset.id"))
            sequence_id = str(uuid.uuid4()) if source_id in used_ids else source_id
            used_ids.add(sequence_id)
            sequence.pop("sequence_items", None)
            sequence.update(id=sequence_id, preset_name=sequence.get("preset_name", Path(path).stem), sequence_steps=steps)
            sequence["selected"] = set(range(len(steps)))
            sequences.append(sequence)
    if not writers and not sequences:
        raise ValueError(qtTrId("listener.error.empty"))
    progress(1)
    return writers, sequences


def export_recording(path, samples, progress, check, writer_label, type_snapshots):
    from module_handler import DataModelHandler

    # These handlers/models are created and used on the export worker only.
    handlers = {}
    groups, ordered = {}, []
    for index, entry in enumerate(samples):
        if index % 1000 == 0:
            check()
            progress(0.2 * index / max(1, len(samples)))
        if not entry["validData"] and entry.get("operation") != "dispose":
            continue
        if "replay" not in entry:
            raise ValueError(entry.get("replayError", qtTrId("listener.error.message")))
        ordered.append(entry)
    if not ordered:
        raise ValueError(qtTrId("listener.error.samples"))
    ordered.sort(key=lambda entry: entry["replay"]["received_monotonic_ns"])
    ids = []
    for index, entry in enumerate(ordered):
        if index % 1000 == 0:
            check()
            progress(0.2 + 0.1 * index / len(ordered))
        reader = entry["replay"]["reader"]
        key = (reader.id, entry["replay"]["writer_identity"], reader.domainId, reader.topic_name,
               reader.topic_type, json.dumps(reader.qos, sort_keys=True))
        if key not in groups:
            groups[key] = {"id": str(uuid.uuid4()), "preset_name": reader.topic_name, "description": "",
                           "domain_id": reader.domainId, "topic_name": reader.topic_name,
                           "topic_type": reader.topic_type, "qos": reader.qos, "indices": []}
        group = groups[key]
        ids.append(group["id"] if not group["indices"] else str(uuid.uuid4()))
        group["indices"].append(index)
    topics, counters = {}, {}
    for group in groups.values():
        topics[group["topic_name"]] = topics.get(group["topic_name"], 0) + 1
    done, count = [0], len(ordered) * 3
    def advanced():
        done[0] += 1
        if done[0] % 1000 == 0:
            progress(0.3 + 0.7 * done[0] / count)
    def message(index):
        entry = ordered[index]
        sample_type = entry["sampleType"]
        if sample_type not in handlers:
            handlers[sample_type] = DataModelHandler.fromTypeSnapshot(type_snapshots[sample_type])
        sample = sample_type.deserialize(entry["sampleCdr"])
        value = handlers[sample_type].sampleToJson(entry["topicType"], sample)
        value.update(id=ids[index], name=str(index + 1), source_timestamp=entry["sourceTimestamp"],
                     received_timestamp=entry["receivedTimestamp"])
        advanced()
        return value
    def presets():
        for group in groups.values():
            topic = group["topic_name"]
            if topics[topic] > 1:
                counters[topic] = counters.get(topic, 0) + 1
                group["preset_name"] = f"{topic} - {writer_label} {counters[topic]}"
            indices = group["indices"]
            yield {**{key: value for key, value in group.items() if key != "indices"},
                   "message": message(indices[0]),
                   "messages": JsonArray(len(indices) - 1, lambda indices=indices: (message(index) for index in indices[1:]))}
    def steps():
        previous = ordered[0]["replay"]["received_monotonic_ns"]
        for index, entry in enumerate(ordered):
            current = entry["replay"]["received_monotonic_ns"]
            advanced()
            yield {"message_id": ids[index], "operation": entry["operation"], "delay_ms": (current - previous) / 1_000_000}
            previous = current
    def legacy():
        for index, entry in enumerate(ordered):
            advanced()
            if entry["operation"] == "write":
                yield ids[index]
    write_count = sum(entry["operation"] == "write" for entry in ordered)
    document = {"presets": JsonArray(len(groups), presets), "sequence_presets": [{"id": str(uuid.uuid4()),
                "preset_name": Path(path).stem, "description": "", "sequence_steps": JsonArray(len(ordered), steps),
                "sequence_items": JsonArray(write_count, legacy)}]}
    save_json(path, document, check)
    progress(1)


def export_presets(path, presets, sequences, progress, check):
    total = sum(len(preset["messages"]) for preset in presets) or 1
    done = [0]
    def messages(preset, first=0):
        for index in range(first, len(preset["messages"])):
            check()
            message = dict(preset["messages"][index])
            message.update(id=preset["ids"][index], name=preset["names"][index])
            done[0] += 1
            if done[0] % 1000 == 0:
                progress(done[0] / total)
            yield message
    def writers():
        for preset in presets:
            yield {**{key: value for key, value in preset.items() if key not in ("messages", "ids", "names")},
                   "message": next(messages(preset)),
                   "messages": JsonArray(len(preset["messages"]) - 1, lambda preset=preset: messages(preset, 1))}
    sequence_data = []
    for sequence in sequences:
        steps = sequence["sequence_steps"]
        sequence_data.append({**sequence, "sequence_steps": JsonArray(len(steps), lambda steps=steps: iter(steps)),
                              "sequence_items": JsonArray(sum(step["operation"] == "write" for step in steps),
                                                          lambda steps=steps: (step["message_id"] for step in steps if step["operation"] == "write"))})
    save_json(path, {"presets": JsonArray(len(presets), writers), "sequence_presets": sequence_data}, check)
    progress(1)
