"""
 * Copyright(c) 2024 Sven Trittler
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
from pathlib import Path
import time
import uuid

from models.data_tree_model import DataTreeModel

from loguru import logger as logging

from PySide6.QtCore import qtTrId, Qt, QModelIndex, QAbstractListModel, Property, Signal, Slot, QSaveFile, QIODevice


class ReceiverModel(QAbstractListModel):

    ReaderIdRole = Qt.UserRole + 1
    ReceivedMsgRole = Qt.UserRole + 2
    SampleInfoRole = Qt.UserRole + 3
    ValidDataRole = Qt.UserRole + 4
    SourceTimestampRole = Qt.UserRole + 5
    TransmissionTimeRole = Qt.UserRole + 6
    ReceivedTimestampRole = Qt.UserRole + 7
    WriterIdRole = Qt.UserRole + 8
    DdsReaderIdRole = Qt.UserRole + 9
    WriterApplicationRole = Qt.UserRole + 10
    WriterHostnameRole = Qt.UserRole + 11
    WriterProcessIdRole = Qt.UserRole + 12
    WriterAddressesRole = Qt.UserRole + 13
    TopicTypeRole = Qt.UserRole + 14
    TopicNameRole = Qt.UserRole + 15

    StructuredRole = Qt.UserRole + 16
    instanceViewChanged = Signal()
    operationError = Signal(str)
    replayChanged = Signal()
    watchChanged = Signal()


    def __init__(self, dataModelHandler=None, listenerModel=None, parent=None):
        super().__init__(parent)
        self.watches = set()
        self.watchExclusions = set()
        self.dataModelHandler = dataModelHandler
        self.listenerModel = listenerModel
        self._replay_count = 0
        self._messages = []
        self._instances = []
        self._instance_rows = {}
        self._instance_view = False

    @Property(bool, notify=instanceViewChanged)
    def instanceView(self):
        return self._instance_view

    @instanceView.setter
    def instanceView(self, enabled):
        if self._instance_view == enabled:
            return
        self.beginResetModel()
        self._instance_view = enabled
        self.endResetModel()
        self.instanceViewChanged.emit()

    def _visible_messages(self):
        return self._instances if self._instance_view else self._messages

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._visible_messages())

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None

        item = self._visible_messages()[index.row()]

        if role == self.StructuredRole:
            return item.get("structured", {})
        if role == self.ReaderIdRole:
            return item["readerId"]
        if role == self.ReceivedMsgRole:
            return item["msg"]
        if role == self.SampleInfoRole:
            return item["sampleInfo"]
        if role == self.ValidDataRole:
            return item["validData"]
        if role == self.SourceTimestampRole:
            return item["sourceTimestamp"]
        if role == self.TransmissionTimeRole:
            return item["transmissionTime"]
        if role == self.ReceivedTimestampRole:
            return item["receivedTimestamp"]
        if role == self.WriterIdRole:
            return item["writerId"]
        if role == self.DdsReaderIdRole:
            return item["ddsReaderId"]
        if role == self.WriterApplicationRole:
            return item["writerApplication"]
        if role == self.WriterHostnameRole:
            return item["writerHostname"]
        if role == self.WriterProcessIdRole:
            return item["writerProcessId"]
        if role == self.WriterAddressesRole:
            return item["writerAddresses"]
        if role == self.TopicTypeRole:
            return item["topicType"]
        if role == self.TopicNameRole:
            return item["topicName"]

        return None

    def roleNames(self):
        return {
            self.StructuredRole: b"structured",
            self.ReaderIdRole: b"readerId",
            self.ReceivedMsgRole: b"receivedMsg",
            self.SampleInfoRole: b"sampleInfo",
            self.ValidDataRole: b"validData",
            self.SourceTimestampRole: b"sourceTimestamp",
            self.TransmissionTimeRole: b"transmissionTime",
            self.ReceivedTimestampRole: b"receivedTimestamp",
            self.WriterIdRole: b"writerId",
            self.DdsReaderIdRole: b"ddsReaderId",
            self.WriterApplicationRole: b"writerApplication",
            self.WriterHostnameRole: b"writerHostname",
            self.WriterProcessIdRole: b"writerProcessId",
            self.WriterAddressesRole: b"writerAddresses",
            self.TopicTypeRole: b"topicType",
            self.TopicNameRole: b"topicName"
        }


    @Slot(str, str, str, bool, str, str, str, str, str, str, str, str, str, str,
          str, str, object)
    def addReceivedMsg(self, readerId, msg, sampleInfo, validData,
                       sourceTimestamp, transmissionTime, receivedTimestamp,
                       writerId, ddsReaderId, writerApplication,
                       writerHostname, writerProcessId, writerAddresses,
                       topicType, topicName, instanceHandle, sample=None):
        item = {
            "readerId": readerId,
            "msg": msg,
            "sampleInfo": sampleInfo,
            "validData": validData,
            "sourceTimestamp": sourceTimestamp,
            "transmissionTime": transmissionTime,
            "receivedTimestamp": receivedTimestamp,
            "writerId": writerId,
            "ddsReaderId": ddsReaderId,
            "writerApplication": writerApplication,
            "writerHostname": writerHostname,
            "writerProcessId": writerProcessId,
            "writerAddresses": writerAddresses,
            "topicType": topicType,
            "topicName": topicName,
        }
        received_monotonic_ns = time.monotonic_ns()
        if isinstance(sample, dict) and "sample" in sample:
            received_monotonic_ns = sample["received_monotonic_ns"]
            sample = sample["sample"]
        if validData and sample is not None and self.dataModelHandler is not None:
            tree = None
            try:
                missing = set()
                root = self.dataModelHandler.getRootNode(topicType, missing)
                if missing:
                    raise ValueError(qtTrId("listener.error.types").replace("%1", ", ".join(sorted(missing))))
                tree = DataTreeModel(root)
                tree.fromDataObject(sample, self.dataModelHandler)
                item["structured"] = tree.toJson()
                reader = self.listenerModel.readers.get(readerId) if self.listenerModel else None
                if reader is None:
                    raise ValueError(qtTrId("listener.error.reader"))
                item["replay"] = {
                    "received_monotonic_ns": received_monotonic_ns,
                    "reader": copy.deepcopy(reader),
                }
            except Exception as error:
                logging.error(f"Cannot serialize received sample: {error}")
                item["replayError"] = str(error)
            finally:
                if tree is not None:
                    tree.deleteLater()
        # DDS handles identify keyed (including composite-key) and unkeyed
        # instances within a reader, independently of their publishing writer.
        key = (readerId, instanceHandle)
        instance_row = self._instance_rows.get(key)
        is_new = instance_row is None
        row = len(self._instances) if self._instance_view else len(self._messages)
        inserting = not self._instance_view or is_new
        if inserting:
            self.beginInsertRows(QModelIndex(), row, row)

        self._messages.append(item)
        if validData:
            self._replay_count += 1
        if is_new:
            self._instance_rows[key] = len(self._instances)
            self._instances.append(item)
        else:
            self._instances[instance_row] = item

        if inserting:
            self.endInsertRows()
        else:
            index = self.index(instance_row, 0)
            self.dataChanged.emit(index, index, list(self.roleNames()))
        if validData:
            self.replayChanged.emit()


    @Slot()
    def clear(self):
        self.beginResetModel()

        self._messages.clear()
        self._instances.clear()
        self._instance_rows.clear()
        self._replay_count = 0

        self.endResetModel()
        self.replayChanged.emit()

    @Slot(str)
    def exportToFile(self, filePath):
        logging.info(f"Export messages to file: {filePath}")
        try:
            with open(filePath, "w", encoding="utf-8") as f:
                for item in self._messages:
                    f.write(f"[{item['receivedTimestamp']}]  -  {item['msg']}\n")
        except Exception as e:
            logging.error(f"Error exporting messages to file: {e}")

    @Property(int, notify=replayChanged)
    def replayCount(self):
        return self._replay_count

    @Slot(str)
    def exportReplay(self, filePath):
        try:
            samples = [item for item in self._messages if item["validData"]]
            if not samples:
                raise ValueError(qtTrId("listener.error.samples"))
            for item in samples:
                if "replay" not in item:
                    raise ValueError(item.get("replayError", qtTrId("listener.error.message")))
            samples.sort(key=lambda item: item["replay"]["received_monotonic_ns"])
            start_ns = samples[0]["replay"]["received_monotonic_ns"]
            presets = {}
            timeline = []
            for entry in samples:
                reader = entry["replay"]["reader"]
                key = (reader.id, reader.domainId, reader.topic_name, reader.topic_type,
                       json.dumps(reader.qos, sort_keys=True))
                if key not in presets:
                    presets[key] = {
                        "id": str(uuid.uuid4()), "preset_name": reader.topic_name,
                        "description": "", "domain_id": reader.domainId,
                        "topic_name": reader.topic_name, "topic_type": reader.topic_type,
                        "qos": reader.qos, "messages": [],
                    }
                preset = presets[key]
                message = copy.deepcopy(entry["structured"])
                message["id"] = preset["id"] if "message" not in preset else str(uuid.uuid4())
                message["name"] = str(len(timeline) + 1)
                message["source_timestamp"] = entry["sourceTimestamp"]
                message["received_timestamp"] = entry["receivedTimestamp"]
                if "message" not in preset:
                    preset["message"] = message
                else:
                    preset["messages"].append(message)
                timeline.append({"preset_id": preset["id"], "message_id": message["id"],
                                 "offset_ms": (entry["replay"]["received_monotonic_ns"] - start_ns) / 1_000_000})
            sequence = {"id": str(uuid.uuid4()), "preset_name": Path(filePath).stem,
                        "description": "", "sequence_items": [event["message_id"] for event in timeline]}
            payload = {"presets": list(presets.values()), "sequence_presets": [sequence],
                       "replay": {"version": 1, "interval_ms": 100,
                                  "use_original_timing": False, "events": timeline}}
            content = json.dumps(payload, indent=4).encode("utf-8")
            output = QSaveFile(filePath)
            if not output.open(QIODevice.WriteOnly):
                raise OSError(output.errorString())
            if output.write(content) != len(content):
                output.cancelWriting()
                raise OSError(output.errorString())
            if not output.commit():
                raise OSError(output.errorString())
        except Exception as error:
            self.operationError.emit(qtTrId("listener.error.export").replace("%1", str(error)))

    @Slot()
    def clearWatchlist(self):
        self.watches.clear()
        self.watchExclusions.clear()
        self.watchChanged.emit()
