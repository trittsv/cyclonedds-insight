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
import time

from models.data_tree_model import DataTreeModel

from loguru import logger as logging
from utils.preset_io import PresetIo, export_recording

from PySide6.QtCore import qtTrId, Qt, QModelIndex, QAbstractListModel, Property, Signal, Slot


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
    MessageNumberRole = Qt.UserRole + 17
    DomainIdRole = Qt.UserRole + 18
    StructuredJsonRole = Qt.UserRole + 19
    HasStructuredRole = Qt.UserRole + 20
    instanceViewChanged = Signal()
    operationError = Signal(str)
    replayChanged = Signal()
    messageCountChanged = Signal()
    watchChanged = Signal()
    exportFinished = Signal(bool)


    def __init__(self, dataModelHandler=None, listenerModel=None, parent=None, presetIo=None):
        super().__init__(parent)
        self.presetIo = presetIo if presetIo is not None else PresetIo(self)
        self.watches = set()
        self.watchExclusions = set()
        self.dataModelHandler = dataModelHandler
        self.listenerModel = listenerModel
        self._replay_count = 0
        self._received_total = 0
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

        if role == self.DomainIdRole:
            return item["domainId"]
        if role == self.MessageNumberRole:
            return item["messageNumber"]
        if role == self.HasStructuredRole:
            return bool(item.get("structured"))
        if role == self.StructuredJsonRole:
            return json.dumps(item.get("structured", {}), ensure_ascii=False)
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
            self.StructuredJsonRole: b"structuredJson",
            self.HasStructuredRole: b"hasStructured",
            self.MessageNumberRole: b"messageNumber",
            self.DomainIdRole: b"domainId",
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
        self._received_total += 1
        reader = self.listenerModel.readers.get(readerId) if self.listenerModel else None
        domain_id = reader.domainId if reader else -1
        if isinstance(sample, dict):
            domain_id = sample.get("domain_id", domain_id)
        operation = "write" if validData else None
        if not validData and isinstance(sample, dict):
            operation = sample.get("operation")
        recordable = validData or operation == "dispose"
        item = {
            "operation": operation,
            "domainId": domain_id,
            "messageNumber": self._received_total,
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
        writer_identity = ("guid", writerId)
        if isinstance(sample, dict) and "sample" in sample:
            received_monotonic_ns = sample["received_monotonic_ns"]
            publication_handle = sample.get("publication_handle")
            if isinstance(publication_handle, int) and publication_handle > 0:
                # Discovery may temporarily provide no GUID, including after a
                # writer disappears. The DDS publication handle stays unchanged.
                writer_identity = ("publication", publication_handle)
            sample = sample["sample"]
        if sample is not None and self.dataModelHandler is not None:
            tree = None
            try:
                missing = set()
                root = self.dataModelHandler.getRootNode(topicType, missing)
                if missing:
                    raise ValueError(qtTrId("listener.error.types").replace("%1", ", ".join(sorted(missing))))
                tree = DataTreeModel(root)
                tree.fromDataObject(sample, self.dataModelHandler)
                structured = tree.toJson()
                item["structured"] = structured
                if recordable:
                    if reader is None:
                        raise ValueError(qtTrId("listener.error.reader"))
                    item["replay"] = {
                        "received_monotonic_ns": received_monotonic_ns,
                        "writer_identity": writer_identity,
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
        if recordable:
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
        self.messageCountChanged.emit()
        if recordable:
            self.replayChanged.emit()


    @Slot()
    def clear(self):
        self.beginResetModel()

        self._messages.clear()
        self._instances.clear()
        self._instance_rows.clear()
        self._replay_count = 0
        self._received_total = 0

        self.endResetModel()
        self.messageCountChanged.emit()
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

    @Property(int, notify=messageCountChanged)
    def totalReceivedCount(self):
        return self._received_total

    @Property(int, notify=messageCountChanged)
    def messageCount(self):
        return len(self._messages)

    @Property(int, notify=replayChanged)
    def replayCount(self):
        return self._replay_count

    @Slot(str, result=bool)
    def exportReplay(self, filePath):
        if self.presetIo.busy:
            self.operationError.emit(qtTrId("preset.io.busy"))
            return False
        # Received entries and their reader/structured snapshots are immutable.
        # A shallow tuple fixes the export boundary while reception can continue.
        samples = tuple(self._messages)
        writer_label = qtTrId("entity.writer")
        started = self.presetIo.start("export", lambda progress, check:
                                      export_recording(filePath, samples, progress, check, writer_label),
                                      self._exportDone)
        if not started:
            self.operationError.emit(qtTrId("preset.io.busy"))
        return started

    def _exportDone(self, result, error):
        if error is not None:
            self.operationError.emit(qtTrId("listener.error.export").replace("%1", error))
        self.exportFinished.emit(error is None)

    @Slot()
    def clearWatchlist(self):
        self.watches.clear()
        self.watchExclusions.clear()
        self.watchChanged.emit()
