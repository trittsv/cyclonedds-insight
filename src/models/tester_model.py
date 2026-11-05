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

from PySide6.QtCore import Qt, QModelIndex, QAbstractListModel, Qt, QByteArray, QStandardPaths, QFile, QDir, QThread, Property
from PySide6.QtCore import QObject, Signal, Slot, qtTrId
from loguru import logger as logging
import os
import sys
import importlib
import copy
from pathlib import Path
import uuid
import glob
from dataclasses import dataclass
import typing
from dds_access.dispatcher import DispatcherThread
from cyclonedds.core import Qos, Policy
from cyclonedds.util import duration
import types
from PySide6.QtQml import qmlRegisterType
from models.data_tree_model import DataTreeModel, DataTreeNode
from models.sequence_playback import SequencePlayback
from utils.qml_utils import QmlUtils
from utils.sequence_utils import sequence_fields, sequence_steps
from utils.preset_io import PresetIo, load_presets, export_presets

import json

class SequenceItem(QAbstractListModel):
    NameRole = Qt.UserRole + 1
    DataItemIdRole = Qt.UserRole + 2
    OperationRole = Qt.UserRole + 3
    DelayRole = Qt.UserRole + 4
    SelectedRole = Qt.UserRole + 5
    selectionChanged = Signal()
    countChanged = Signal()
    changed = Signal()

    def __init__(self, presetName, description="", parent=None):
        super().__init__(parent)
        self.presetName = presetName
        self.description = description
        self._steps = []
        self._selected = set()
        self._locked = False

    @property
    def sequenceSteps(self):
        return self._steps

    @sequenceSteps.setter
    def sequenceSteps(self, steps):
        self._steps = steps
        self._selected = set(range(len(steps)))
        self.selectionChanged.emit()
        self.countChanged.emit()

    @property
    def sequenceItems(self):
        return [step["message_id"] for step in self._steps]

    @Property(int, notify=countChanged)
    def count(self):
        return len(self._steps)

    @Property(bool, notify=changed)
    def locked(self):
        return self._locked

    def setLocked(self, locked):
        if self._locked != locked:
            self._locked = locked
            self.changed.emit()

    @Property(int, notify=selectionChanged)
    def selectedCount(self):
        return len(self._selected)

    @Property(list, notify=selectionChanged)
    def selectedRows(self):
        return sorted(self._selected)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or not 0 <= index.row() < len(self._steps):
            return None
        step = self._steps[index.row()]
        if role in (self.NameRole, self.DataItemIdRole, Qt.DisplayRole):
            return step["message_id"]
        if role == self.OperationRole:
            return step["operation"]
        if role == self.DelayRole:
            return step.get("delay_ms", 0)
        if role == self.SelectedRole:
            return index.row() in self._selected
        return None

    def roleNames(self):
        return {self.NameRole: b'name', self.DataItemIdRole: b'dataItemId',
                self.OperationRole: b'operation', self.DelayRole: b'delayMs',
                self.SelectedRole: b'stepSelected'}

    def rowCount(self, index=QModelIndex()):
        return 0 if index.isValid() else len(self._steps)

    def getPresetName(self):
        return self.presetName

    def setPresetName(self, presetName):
        self.presetName = presetName

    def getDescription(self):
        return self.description

    def setDescription(self, description):
        self.description = description

    @Slot(str)
    def addSequenceItem(self, dataItemId):
        if self._locked:
            return
        row = len(self._steps)
        self.beginInsertRows(QModelIndex(), row, row)
        self._steps.append({"message_id": dataItemId, "operation": "write", "delay_ms": 0})
        self._selected.add(row)
        self.endInsertRows()
        self.countChanged.emit()
        self.selectionChanged.emit()

    @Slot(int)
    def removeSequenceItem(self, index):
        if self._locked or not 0 <= index < len(self._steps):
            return
        self.beginRemoveRows(QModelIndex(), index, index)
        del self._steps[index]
        self._selected = {row - 1 if row > index else row for row in self._selected if row != index}
        self.endRemoveRows()
        self.countChanged.emit()
        self.selectionChanged.emit()

    @Slot(int, int, result=int)
    def moveStep(self, row, direction):
        target = row + direction
        if self._locked or not 0 <= row < len(self._steps) or not 0 <= target < len(self._steps):
            return row
        if target == row:
            return row
        selected = [index in self._selected for index in range(len(self._steps))]
        self.beginMoveRows(QModelIndex(), row, row, QModelIndex(), target + 1 if target > row else target)
        self._steps.insert(target, self._steps.pop(row))
        selected.insert(target, selected.pop(row))
        self._selected = {index for index, value in enumerate(selected) if value}
        self.endMoveRows()
        self.selectionChanged.emit()
        return target

    @Slot(int, str)
    def setOperation(self, row, operation):
        if self._locked or not 0 <= row < len(self._steps) or operation not in ("write", "dispose"):
            return
        if self._steps[row]["operation"] != operation:
            self._steps[row]["operation"] = operation
            index = self.index(row, 0)
            self.dataChanged.emit(index, index, [self.OperationRole])

    @Slot(int, float)
    def setDelay(self, row, delay):
        if self._locked or not 0 <= row < len(self._steps):
            return
        try:
            step = sequence_steps({"sequence_steps": [dict(self._steps[row], delay_ms=delay)]})[0]
        except ValueError:
            return
        if step["delay_ms"] != self._steps[row].get("delay_ms", 0):
            self._steps[row] = step
            index = self.index(row, 0)
            self.dataChanged.emit(index, index, [self.DelayRole])

    @Slot(int, bool)
    def setSelected(self, row, selected):
        if self._locked or not 0 <= row < len(self._steps):
            return
        if selected:
            self._selected.add(row)
        else:
            self._selected.discard(row)
        index = self.index(row, 0)
        self.dataChanged.emit(index, index, [self.SelectedRole])
        self.selectionChanged.emit()

    @Slot(bool)
    def selectAll(self, selected):
        if self._locked:
            return
        self._selected = set(range(len(self._steps))) if selected else set()
        if self._steps:
            self.dataChanged.emit(self.index(0, 0), self.index(len(self._steps) - 1, 0), [self.SelectedRole])
        self.selectionChanged.emit()

    def updateReferences(self, removed, promoted=None):
        promoted = promoted or {}
        steps, selected = [], set()
        for row, step in enumerate(self._steps):
            reference = step["message_id"]
            if reference in removed:
                continue
            if row in self._selected:
                selected.add(len(steps))
            steps.append(dict(step, message_id=promoted[reference]) if reference in promoted else step)
        if steps == self._steps:
            return
        self.beginResetModel()
        self._steps, self._selected = steps, selected
        self.endResetModel()
        self.countChanged.emit()
        self.selectionChanged.emit()


class MessageMetadata:
    def __init__(self, messages):
        self.messages = messages

    def __len__(self):
        return len(self.messages)

    def __getitem__(self, index):
        message = self.messages[index]
        return {key: message[key] for key in ("source_timestamp", "received_timestamp") if key in message}


class MessageSnapshots:
    def __init__(self, writer):
        self.original = writer._serializedMessages[:]
        self.edited = {index: writer.messageSnapshot(index) for index, model in enumerate(writer.dataTreeModels)
                       if model is not None}

    def __len__(self):
        return len(self.original)

    def __getitem__(self, index):
        if index in self.edited:
            return self.edited[index]
        message = self.original[index]
        return {key: message[key] for key in ("root", "source_timestamp", "received_timestamp") if key in message}


class WriterItem:
    def __init__(self, writerId, domainId, topic_name, topic_type, qmlCode, pyCode, dataTreeModels, presetName, qos={}, description="", dataItemNames=None, dataItemIds=None, messageMetadata=None):
        self.writerId = writerId
        self.domainId = domainId
        self.topic_name = topic_name
        self.topic_type = topic_type
        self.qmlCode = qmlCode
        self.pyCode = pyCode
        self.dataTreeModels = dataTreeModels
        self._serializedMessages = [{} for _ in dataTreeModels]
        self._factory = None
        if messageMetadata:
            for index in range(len(dataTreeModels)):
                if index < len(messageMetadata):
                    self._serializedMessages[index].update(copy.deepcopy(messageMetadata[index]))
        self.messageMetadata = MessageMetadata(self._serializedMessages)
        self.dataItemNames = [
            str(name).strip() or f"Data {index + 1}"
            for index, name in enumerate(dataItemNames)
        ] if isinstance(dataItemNames, list) else []
        while len(self.dataItemNames) < len(self.dataTreeModels):
            self.dataItemNames.append(f"Data {len(self.dataItemNames) + 1}")
        self.dataItemNames = self.dataItemNames[:len(self.dataTreeModels)]
        importedDataItemIds = list(dataItemIds) if isinstance(dataItemIds, list) else []
        self.dataItemIds = []
        seen_ids = set()
        for dataIndex in range(len(self.dataTreeModels)):
            dataItemId = writerId if dataIndex == 0 else (
                importedDataItemIds[dataIndex]
                if dataIndex < len(importedDataItemIds)
                else ""
            )
            if not dataItemId or dataItemId in seen_ids:
                dataItemId = str(uuid.uuid4())
            self.dataItemIds.append(dataItemId)
            seen_ids.add(dataItemId)
        self._reindex()
        self.presetName = presetName
        self.description = description
        self.qos = qos
        self.isStarted = False

    @classmethod
    def fromImported(cls, preset, factory):
        item = cls.__new__(cls)
        item.writerId = preset["id"]
        item.domainId = preset["domain_id"]
        item.topic_name, item.topic_type = preset["topic_name"], preset["topic_type"]
        item.qmlCode = item.pyCode = None
        item.presetName = preset.get("preset_name", item.topic_name)
        item.description = preset.get("description", "")
        item.qos = preset["qos"]
        item.isStarted = False
        item._serializedMessages = preset["messages"]
        item._factory = factory
        item.dataTreeModels = [None] * len(item._serializedMessages)
        item.dataItemIds, item.dataItemNames = preset["ids"], preset["names"]
        item._dataIndices = preset["index_by_id"]
        item.messageMetadata = MessageMetadata(item._serializedMessages)
        return item

    def _reindex(self):
        self._dataIndices = {value: index for index, value in enumerate(self.dataItemIds)}

    def messageSnapshot(self, index):
        model = self.dataTreeModels[index]
        value = model.toJson() if model is not None else {"root": self._serializedMessages[index]["root"]}
        return dict(self.messageMetadata[index], **value)

    def exportSnapshot(self):
        # Imported roots are immutable; edited trees are serialized on their UI
        # thread before the worker starts. Unopened messages need no Qt objects.
        return {"id": self.writerId, "domain_id": self.domainId, "topic_name": self.topic_name,
                "topic_type": self.topic_type, "preset_name": self.presetName, "description": self.description,
                "qos": self.qos, "messages": MessageSnapshots(self),
                "ids": self.dataItemIds[:], "names": self.dataItemNames[:]}

    def getPresetName(self):
        return self.presetName

    def setPresetName(self, presetName):
        self.presetName = presetName

    def getDescription(self):
        return self.description

    def setDescription(self, description):
        self.description = description

    def getTopicName(self):
        return self.topic_name
    
    def getTopicType(self):
        return self.topic_type
    
    def getDomainId(self):
        return self.domainId

    def getDataTreeModel(self, dataIndex=0):
        if dataIndex < 0 or dataIndex >= len(self.dataTreeModels):
            return None
        if self.dataTreeModels[dataIndex] is None:
            self.dataTreeModels[dataIndex] = self._factory(self.topic_type, self._serializedMessages[dataIndex]["root"])
        return self.dataTreeModels[dataIndex]

    def getDataTreeModels(self):
        return [self.getDataTreeModel(index) for index in range(self.getDataTreeModelCount())]

    def loadedTrees(self):
        return (model for model in self.dataTreeModels if model is not None)

    def addDataTreeModel(self, dataTreeModel, name=None, dataItemId=None):
        self.dataTreeModels.append(dataTreeModel)
        self._serializedMessages.append({})
        self.dataItemNames.append(name or f"Data {len(self.dataTreeModels)}")
        self.dataItemIds.append(dataItemId or str(uuid.uuid4()))
        self._reindex()

    def insertDataTreeModel(self, dataIndex, dataTreeModel, name=None, dataItemId=None, metadata=None):
        self.dataTreeModels.insert(dataIndex, dataTreeModel)
        self._serializedMessages.insert(dataIndex, copy.deepcopy(metadata or {}))
        self.dataItemNames.insert(dataIndex, name or f"Data {dataIndex + 1}")
        self.dataItemIds.insert(dataIndex, dataItemId or str(uuid.uuid4()))
        self._reindex()

    def removeDataTreeModel(self, dataIndex):
        if len(self.dataTreeModels) <= 1 or dataIndex < 0 or dataIndex >= len(self.dataTreeModels):
            return "", ""
        dataTreeModel = self.dataTreeModels.pop(dataIndex)
        del self._serializedMessages[dataIndex]
        del self.dataItemNames[dataIndex]
        removedDataItemId = self.dataItemIds.pop(dataIndex)
        promotedDataItemId = ""
        if dataIndex == 0:
            promotedDataItemId = self.dataItemIds[0]
            self.dataItemIds[0] = self.writerId
        if dataTreeModel is not None:
            dataTreeModel.deleteLater()
        self._reindex()
        return removedDataItemId, promotedDataItemId

    def getDataTreeModelCount(self):
        return len(self.dataTreeModels)

    def getDataItemName(self, dataIndex):
        if dataIndex < 0 or dataIndex >= len(self.dataItemNames):
            return ""
        return self.dataItemNames[dataIndex]

    def setDataItemName(self, dataIndex, name):
        if dataIndex < 0 or dataIndex >= len(self.dataItemNames):
            return
        self.dataItemNames[dataIndex] = name

    def getDataItemNames(self):
        return self.dataItemNames

    def getDataItemId(self, dataIndex):
        if dataIndex < 0 or dataIndex >= len(self.dataItemIds):
            return ""
        return self.dataItemIds[dataIndex]

    def getDataItemIds(self):
        return self.dataItemIds

    def getDataIndexById(self, dataItemId):
        return self._dataIndices.get(dataItemId, -1)
    
    def getQmlCode(self):
        return self.qmlCode

    def setIsStarted(self, isStarted):
        self.isStarted = isStarted

    def getIsStarted(self):
        return self.isStarted

class TesterModel(QAbstractListModel):

    NameRole = Qt.UserRole + 1
    DataModelRole = Qt.UserRole + 2
    PresetNameRole = Qt.UserRole + 3
    IsPresetSequenceRole = Qt.UserRole + 4
    DescriptionRole = Qt.UserRole + 5
    IsWriterRole = Qt.UserRole + 6
    IsStarted = Qt.UserRole + 7

    showQml = Signal(str, str)
    countChanged = Signal()
    operationError = Signal(str)
    selectionRequested = Signal(int)
    playbackChanged = Signal()
    importFinished = Signal(int)
    recordingImported = Signal(int)
    exportFinished = Signal(bool)

    createEndpointFromTesterSignal = Signal(str, int, str, str, int, str, object, object)

    writeDataSignal = Signal(str, object)
    disposeDataSignal = Signal(str, object)
    unregisterDataSignal = Signal(str, object)

    requestQosJsonSignal = Signal(str, str)

    def getCount(self):
        return self.rowCount()

    count = Property(int, getCount, notify=countChanged)

    untitiledSequenceCount = 1
    untitiledCount = 1

    def __init__(self, threads, dataModelHandler, datamodelRepoModel, parent=QObject(), presetIo=None):
        super().__init__()
        self.dataModelHandler = dataModelHandler
        self.datamodelRepoModel = datamodelRepoModel
        self.createEndpointFromTesterSignal.connect(self.datamodelRepoModel.createEndpointFromTester, Qt.ConnectionType.QueuedConnection)
        self.items = {}
        self.threads = threads
        self.alreadyConnectedDomains = []
        self.pendingQosRequests = {}
        self.presetIo = presetIo if presetIo is not None else PresetIo(self)
        self.presetIo.changed.connect(self._ioChanged)
        self.resetExportData()
        self._pendingStarts = set()
        self._cancelledStarts = set()
        self.datamodelRepoModel.newWriterSignal.connect(self.addWriter)
        self.datamodelRepoModel.endpointFailed.connect(self._startFailed)
        self._playback = SequencePlayback(self)
        self._playback.operationError.connect(self.operationError.emit)
        self._playback.changed.connect(self._playbackChanged)

    @Property(QObject, constant=True)
    def sequencePlayback(self):
        return self._playback

    @Property(bool, notify=playbackChanged)
    def playbackBusy(self):
        return self._playback.busy or self.presetIo.busy

    def _ioChanged(self):
        self._playbackChanged()

    def _playbackChanged(self):
        for item in self.items.values():
            if isinstance(item, SequenceItem):
                item.setLocked(self.playbackBusy)
        self.playbackChanged.emit()

    @Slot(int, bool, int)
    @Slot(int, bool, int, bool)
    def playSequence(self, currentIndex, use_delays, interval, repeat=False):
        if self.presetIo.busy:
            return
        sequence = self.getSequenceModel(currentIndex)
        if sequence is not None:
            self._playback.start(sequence, sequence.selectedRows, use_delays, interval, repeat)

    @Slot(int, int)
    def sendSequenceStep(self, currentIndex, row):
        if self.presetIo.busy:
            return
        sequence = self.getSequenceModel(currentIndex)
        if sequence is not None:
            self._playback.start(sequence, [row], True, 100)

    def _startWriter(self, writer_id):
        item = self.items.get(writer_id)
        if not isinstance(item, WriterItem) or item.getIsStarted() or writer_id in self._pendingStarts:
            return
        self._pendingStarts.add(writer_id)
        self._cancelledStarts.discard(writer_id)
        self.createEndpointFromTesterSignal.emit(writer_id, item.getDomainId(), item.getTopicName(),
                                                 item.getTopicType(), 4, item.getPresetName(), {}, copy.deepcopy(item.qos))

    @Slot(str, str)
    def _startFailed(self, writer_id, error):
        self._pendingStarts.discard(writer_id)
        self._cancelledStarts.discard(writer_id)

    def resetExportData(self):
        self.exportData = { "presets": [], "sequence_presets": [] }

    def _createDataTreeModel(self, topicType, messageRoot=None):
        rootNode = self.dataModelHandler.getRootNode(topicType)
        dataTreeModel = DataTreeModel(rootNode, parent=self)
        try:
            if messageRoot:
                dataTreeModel.fromJson(messageRoot, self.dataModelHandler)
        except Exception:
            dataTreeModel.deleteLater()
            raise
        return dataTreeModel

    def _getDataReference(self, dataItemId):
        for writerId, item in self.items.items():
            if isinstance(item, WriterItem):
                dataIndex = item.getDataIndexById(dataItemId)
                if dataIndex >= 0:
                    return writerId, dataIndex
        return "", -1

    def _getAvailableDataReferences(self):
        references = []
        for writerId, item in self.items.items():
            if isinstance(item, WriterItem):
                references.extend(item.getDataItemIds())
        return references

    def _availableReferenceAt(self, index):
        if index < 0:
            return ""
        for item in self.items.values():
            if isinstance(item, WriterItem):
                if index < item.getDataTreeModelCount():
                    return item.getDataItemId(index)
                index -= item.getDataTreeModelCount()
        return ""

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole):
        if not index.isValid():
            return None
        row = index.row()

        itemId = list(self.items.keys())[row]
        item = self.items[itemId]

        if role == self.NameRole:
            return f"{item.getPresetName()}"
        if role == self.DataModelRole:
            if isinstance(item, WriterItem):
                return self.getTreeModel(row, 0)
        if role == self.PresetNameRole:
            return item.getPresetName()
        if role == self.DescriptionRole:
            return item.getDescription()
        if role == self.IsWriterRole:
            return isinstance(item, WriterItem)
        
        if role == self.IsStarted:
            if isinstance(item, WriterItem):
                return item.getIsStarted()
            if isinstance(item, SequenceItem):
                return self.getIsStarted(index.row())

        return None

    def roleNames(self) -> dict[int, QByteArray]:
        return {
            self.NameRole: b'name',
            self.DataModelRole: b'dataModel',
            self.IsPresetSequenceRole: b'isPresetSequence',
            self.PresetNameRole: b'presetName',
            self.DescriptionRole: b'description',
            self.IsWriterRole: b'isWriter',
            self.IsStarted: b'isStarted'
        }

    def rowCount(self, index: QModelIndex = QModelIndex()) -> int:
        return len(self.items.keys())

    @Slot(int, int, result="QVariant")
    def getTreeModel(self, currentIndex: int, dataIndex: int = 0) -> DataTreeModel:
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return None
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if isinstance(item, WriterItem):
            try:
                return item.getDataTreeModel(dataIndex)
            except Exception as error:
                message = qtTrId("listener.error.message") + ": " + str(error)
                logging.error(message)
                self.operationError.emit(message)
        return None

    @Slot(int, result=int)
    def getDataItemCount(self, currentIndex: int) -> int:
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return 0
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if isinstance(item, WriterItem):
            return item.getDataTreeModelCount()
        return 0

    @Slot(result=int)
    def getAvailableDataItemCount(self) -> int:
        return sum(item.getDataTreeModelCount() for item in self.items.values() if isinstance(item, WriterItem))

    @Slot(int, result=str)
    def getAvailableDataItemName(self, availableIndex: int) -> str:
        reference = self._availableReferenceAt(availableIndex)
        return self.getDataItemDisplayName(reference) if reference else ""

    @Slot(int, result=str)
    def getAvailableDataItemId(self, availableIndex: int) -> str:
        return self._availableReferenceAt(availableIndex)

    @Slot(str, result=str)
    def getDataItemDisplayName(self, dataItemId: str) -> str:
        writerId, dataIndex = self._getDataReference(dataItemId)
        item = self.items.get(writerId)
        if not isinstance(item, WriterItem):
            return "Unknown"
        return f"{item.getPresetName()} - {item.getDataItemName(dataIndex)}"

    @Slot(int, int, result=str)
    def getDataItemName(self, currentIndex: int, dataIndex: int) -> str:
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return ""
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if isinstance(item, WriterItem):
            return item.getDataItemName(dataIndex)
        return ""

    @Slot(int, int, str)
    def setDataItemName(self, currentIndex: int, dataIndex: int, name: str):
        if self.playbackBusy:
            return
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if not isinstance(item, WriterItem):
            return
        item.setDataItemName(dataIndex, name.strip() or f"Data {dataIndex + 1}")
        idx = self.index(currentIndex, 0)
        self.dataChanged.emit(idx, idx, [self.DataModelRole])

    @Slot(int, result=int)
    def addDataItem(self, currentIndex: int) -> int:
        if self.playbackBusy:
            return
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return -1
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if not isinstance(item, WriterItem):
            return -1

        item.addDataTreeModel(self._createDataTreeModel(item.getTopicType()))
        idx = self.index(currentIndex, 0)
        self.dataChanged.emit(idx, idx, [self.DataModelRole])
        return item.getDataTreeModelCount() - 1

    @Slot(int, int, result=int)
    def duplicateDataItem(self, currentIndex: int, dataIndex: int) -> int:
        if self.playbackBusy:
            return
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return -1
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if not isinstance(item, WriterItem):
            return -1

        sourceModel = item.getDataTreeModel(dataIndex)
        if sourceModel is None:
            return -1

        duplicateIndex = dataIndex + 1
        duplicateModel = self._createDataTreeModel(
            item.getTopicType(), sourceModel.toJson()["root"]
        )
        item.insertDataTreeModel(
            duplicateIndex,
            duplicateModel,
            f"{item.getDataItemName(dataIndex)}-copy",
            metadata=item.messageMetadata[dataIndex]
        )
        idx = self.index(currentIndex, 0)
        self.dataChanged.emit(idx, idx, [self.DataModelRole])
        return duplicateIndex

    @Slot(int, int, result=int)
    def removeDataItem(self, currentIndex: int, dataIndex: int) -> int:
        if self.playbackBusy:
            return
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return -1
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if not isinstance(item, WriterItem):
            return dataIndex
        removedDataItemId, promotedDataItemId = item.removeDataTreeModel(dataIndex)
        if not removedDataItemId:
            return dataIndex

        for sequenceItem in self.items.values():
            if not isinstance(sequenceItem, SequenceItem):
                continue
            promoted = {promotedDataItemId: item.writerId} if promotedDataItemId else {}
            sequenceItem.updateReferences({removedDataItemId}, promoted)

        idx = self.index(currentIndex, 0)
        self.dataChanged.emit(idx, idx, [self.DataModelRole])
        return min(dataIndex, item.getDataTreeModelCount() - 1)

    @Slot(int, result="QVariant")
    def getSequenceModel(self, currentIndex: int) -> SequenceItem:
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return None
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if isinstance(item, SequenceItem):
            return item
        return None

    @Slot(int, result=str)
    def getDescriptionName(self, currentIndex: int) -> str:
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return ""
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if isinstance(item, SequenceItem):
            return "Sequence"
        else:
            return f"Topic: {item.getTopicName()}  |  Type: {item.getTopicType()}  |  Domain: {item.getDomainId()}"

    @Slot(int, result=bool)
    def getIsStarted(self, currentIndex: int) -> bool:
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return False
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if isinstance(item, WriterItem):
            return item.getIsStarted()
        if isinstance(item, SequenceItem):
            if not item.sequenceSteps:
                return False
            for step in item.sequenceSteps:
                dataItemId = step["message_id"]
                itemCurrentId, _ = self._getDataReference(dataItemId)
                if itemCurrentId not in self.items:
                    logging.warning(f"Data item id {dataItemId} not found in items")
                    continue
                itemCurr = self.items[itemCurrentId]
                if isinstance(itemCurr, WriterItem):
                    itemStarted = itemCurr.getIsStarted()
                    if not itemStarted:
                        return False
            return True
        return False

    @Slot(int)
    def stopItem(self, currentIndex: int):
        if self.playbackBusy:
            return
        if currentIndex < 0:
            return
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        self.beginResetModel()
        if isinstance(item, WriterItem):
            for key in self.threads.keys():
                self.threads[key].deleteWriter(mId)
            item.setIsStarted(False)
        if isinstance(item, SequenceItem):
            stoppedWriterIds = set()
            for dataItemId in item.sequenceItems:
                itemCurrentId, _ = self._getDataReference(dataItemId)
                if itemCurrentId in stoppedWriterIds:
                    continue
                stoppedWriterIds.add(itemCurrentId)
                if itemCurrentId not in self.items:
                    logging.warning(f"Data item id {dataItemId} not found in items")
                    continue
                itemCurr = self.items[itemCurrentId]
                if isinstance(itemCurr, WriterItem):
                    for key in self.threads.keys():
                        self.threads[key].deleteWriter(itemCurrentId)
                    itemCurr.setIsStarted(False)
        self.endResetModel()

    @Slot(int)
    def startItem(self, currentIndex: int):
        if self.playbackBusy:
            return
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]

        if isinstance(item, WriterItem):
            self._startWriter(mId)
        elif isinstance(item, SequenceItem):
            for reference in item.sequenceItems:
                writer_id, _ = self._getDataReference(reference)
                self._startWriter(writer_id)

    @Slot(int, result=str)
    def getPresetName(self, currentIndex: int) -> str:
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return
        mId = list(self.items.keys())[int(currentIndex)]
        return self.items[mId].getPresetName()

    @Slot(int, str)
    def setPresetName(self, currentIndex: int, presetName: str):
        if self.playbackBusy:
            return
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        item.setPresetName(presetName)
        idx = self.index(currentIndex)
        self.dataChanged.emit(idx, idx, [self.PresetNameRole, self.NameRole])

    @Slot(int, result=str)
    def getDescription(self, currentIndex: int) -> str:
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return ""
        mId = list(self.items.keys())[int(currentIndex)]
        return self.items[mId].getDescription()

    @Slot(int, str)
    def setDescription(self, currentIndex: int, description: str):
        if self.playbackBusy:
            return
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        item.setDescription(description)
        idx = self.index(currentIndex)
        self.dataChanged.emit(idx, idx, [self.DescriptionRole])

    @Slot(str, int, str, str, object)
    def addWriter(self, id: str, domainId, topic_name, topic_type: str, qos):
        self._pendingStarts.discard(id)
        if id in self._cancelledStarts:
            self._cancelledStarts.discard(id)
            self.threads[domainId].deleteWriter(id)
            return
        logging.info("AddWriter to TesterModel")

        if domainId not in self.alreadyConnectedDomains:
            self.writeDataSignal.connect(self.threads[domainId].write, Qt.ConnectionType.QueuedConnection)
            self.disposeDataSignal.connect(self.threads[domainId].dispose, Qt.ConnectionType.QueuedConnection)
            self.unregisterDataSignal.connect(self.threads[domainId].unregisterInstance, Qt.ConnectionType.QueuedConnection)
            self.alreadyConnectedDomains.append(domainId)

        if id in self.items.keys():
            self.items[id].setIsStarted(True)
            row = list(self.items.keys()).index(id)
            idx = self.index(row, 0)
            self.dataChanged.emit(idx, idx, [self.IsStarted, self.NameRole, self.PresetNameRole])
        else:
            self.beginResetModel()
            dataTreeModel = self._createDataTreeModel(topic_type)
            self.items[id] = WriterItem(id, domainId, topic_name, topic_type, "", None, [dataTreeModel], f"Untitled-{TesterModel.untitiledCount}", qos)
            TesterModel.untitiledCount += 1
            self.items[id].setIsStarted(True)
            self.endResetModel()
            self.countChanged.emit()

    @Slot(int, int, QModelIndex)
    def addArrayItem(self, currentIndex: int, dataIndex: int, currentTreeIndex: QModelIndex):
        if self.playbackBusy:
            return
        logging.debug("Add Array Item")
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        dataTreeModel = item.getDataTreeModel(dataIndex)
        if dataTreeModel is None:
            return
        if currentTreeIndex.isValid():
            item: DataTreeNode = currentTreeIndex.internalPointer()
            if item.itemArrayTypeName:
                targetRole = DataTreeModel.IsSequenceElementRole
                if item.role == DataTreeModel.IsOptionalRole:
                    targetRole = DataTreeModel.IsOptionalElementRole
                itemNode = self.dataModelHandler.toNode(item.itemArrayTypeName, DataTreeNode("", "", targetRole, parent=item))
                dataTreeModel.addArrayItem(currentTreeIndex, itemNode)
            elif item.parentItem.itemArrayTypeName:
                itemNode = self.dataModelHandler.toNode(item.parentItem.itemArrayTypeName, DataTreeNode("", "", DataTreeModel.IsSequenceElementRole, parent=item))
                itemNode.itemArrayTypeName = item.parentItem.itemArrayTypeName
                dataTreeModel.addArrayItem(currentTreeIndex, itemNode)
            else:
                logging.warning("itemArrayTypeName not set")
        else:
            logging.warning("currentTreeIndex not valid")

    @Slot(int, int, QModelIndex)
    def removeArrayItem(self, currentIndex: int, dataIndex: int, currentTreeIndex: QModelIndex):
        if self.playbackBusy:
            return
        logging.debug("Remove Array Item")
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if isinstance(item, WriterItem):
            dataTreeModel = item.getDataTreeModel(dataIndex)
            if dataTreeModel is None:
                return
            if currentTreeIndex.isValid():
                dataTreeModel.removeArrayItem(currentTreeIndex)

    @Slot(int)
    def showTester(self, currentIndex: int):
        if currentIndex < 0 and len(list(self.items.keys())) == 0:
            return
        logging.trace(f"Show Tester pressed on index: {str(currentIndex)}")
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if isinstance(item, WriterItem):
            self.showQml.emit(mId, item.getQmlCode())

    @Slot(int, int)
    def writeData(self, currentIndex: int, dataIndex: int):
        if self.playbackBusy:
            return
        logging.trace(f"Write Data pressed on index: {str(currentIndex)}")
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if isinstance(item, WriterItem):
            dataTreeModel = item.getDataTreeModel(dataIndex)
            if dataTreeModel is not None:
                self.writeDataSignal.emit(mId, dataTreeModel.getDataObj())
        elif isinstance(item, SequenceItem):
            self.playSequence(currentIndex, True, 100)

    @Slot(int, int)
    def disposeData(self, currentIndex: int, dataIndex: int):
        if self.playbackBusy:
            return
        logging.trace(f"Dispose Data pressed on index: {str(currentIndex)}")
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if isinstance(item, WriterItem):
            dataTreeModel = item.getDataTreeModel(dataIndex)
            if dataTreeModel is not None:
                self.disposeDataSignal.emit(mId, dataTreeModel.getDataObj())
        elif isinstance(item, SequenceItem):
            for dataItemId in item.sequenceItems:
                itemCurrentId, sequenceDataIndex = self._getDataReference(dataItemId)
                if itemCurrentId not in self.items:
                    logging.warning(f"Data item id {dataItemId} not found in items")
                    continue
                item = self.items[itemCurrentId]
                if isinstance(item, WriterItem):
                    dataTreeModel = item.getDataTreeModel(sequenceDataIndex)
                    if dataTreeModel is not None:
                        self.disposeDataSignal.emit(itemCurrentId, dataTreeModel.getDataObj())

    @Slot(int, int)
    def unregisterData(self, currentIndex: int, dataIndex: int):
        if self.playbackBusy:
            return
        logging.trace(f"Unregister Data pressed on index: {str(currentIndex)}")
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if isinstance(item, WriterItem):
            dataTreeModel = item.getDataTreeModel(dataIndex)
            if dataTreeModel is not None:
                self.unregisterDataSignal.emit(mId, dataTreeModel.getDataObj())
        elif isinstance(item, SequenceItem):
            for dataItemId in item.sequenceItems:
                itemCurrentId, sequenceDataIndex = self._getDataReference(dataItemId)
                if itemCurrentId not in self.items:
                    logging.warning(f"Data item id {dataItemId} not found in items")
                    continue
                item = self.items[itemCurrentId]
                if isinstance(item, WriterItem):
                    dataTreeModel = item.getDataTreeModel(sequenceDataIndex)
                    if dataTreeModel is not None:
                        self.unregisterDataSignal.emit(itemCurrentId, dataTreeModel.getDataObj())

    @Slot()
    def deleteAllWriters(self):
        if self.playbackBusy:
            return
        self._playback.clear()
        self.beginResetModel()
        self._cancelledStarts.update(self._pendingStarts)
        for item in self.items.values():
            if isinstance(item, WriterItem):
                for tree in item.loadedTrees():
                    tree.deleteLater()
            else:
                item.deleteLater()
        self.items.clear()
        for key in self.threads.keys():
            self.threads[key].deleteAllWriters()
        self.endResetModel()
        self.countChanged.emit()

    @Slot(int)
    def deleteWriter(self, currentIndex: int):
        if self.playbackBusy:
            return
        if currentIndex < 0:
            return
        logging.trace(f"Delete Writer pressed on index: {str(currentIndex)}")
        mId = list(self.items.keys())[int(currentIndex)]
        if mId in self._pendingStarts:
            self._cancelledStarts.add(mId)
        deletedDataItemIds = set()
        item = self.items.get(mId)
        if isinstance(item, WriterItem):
            deletedDataItemIds.update(item.getDataItemIds())
            for tree in item.loadedTrees():
                tree.deleteLater()
        elif isinstance(item, SequenceItem):
            if self._playback.sequence is item:
                self._playback.clear()
            item.deleteLater()
        self.beginResetModel()
        del self.items[mId]
        for sequenceItem in self.items.values():
            if not isinstance(sequenceItem, SequenceItem):
                continue
            sequenceItem.updateReferences(deletedDataItemIds)
        for key in self.threads.keys():
            self.threads[key].deleteWriter(mId)
        self.endResetModel()
        self.countChanged.emit()

    @Slot(str, result=bool)
    def importJson(self, filePath):
        return self._startImport([filePath], False)

    @Slot(list, result=bool)
    def importJsonFiles(self, paths):
        return self._startImport(paths, False)

    @Slot(str, result=bool)
    def importRecordReplay(self, filePath):
        return self._startImport([filePath], True)

    def _startImport(self, paths, recording):
        if self.playbackBusy or self._pendingStarts:
            self.operationError.emit(qtTrId("preset.io.busy"))
            return False
        if not paths:
            return False
        available = self._getAvailableDataReferences()
        used_ids = list(self.items)
        return self.presetIo.start("import", lambda progress, check:
                                   load_presets(paths, recording, used_ids, available, progress, check),
                                   lambda result, error: self._importDone(result, error, recording))

    def _importDone(self, result, error, recording):
        selected_index = -1
        sequences = []
        try:
            if error is not None:
                raise ValueError(error)
            writers, sequence_presets = result
            for typename in {preset["topic_type"] for preset in writers}:
                missing = set()
                self.dataModelHandler.getRootNode(typename, missing)
                if missing:
                    raise ValueError(qtTrId("listener.error.types").replace("%1", ", ".join(sorted(missing))))
            staged = {preset["id"]: WriterItem.fromImported(preset, self._createDataTreeModel) for preset in writers}
            for preset in sequence_presets:
                sequence = SequenceItem(preset["preset_name"], preset.get("description", ""), self)
                sequences.append(sequence)
                sequence._steps = preset["sequence_steps"]
                sequence._selected = preset["selected"]
                staged[preset["id"]] = sequence
            self.beginResetModel()
            self.items.update(staged)
            self.endResetModel()
            self.countChanged.emit()
            selected = sequence_presets[0]["id"] if sequence_presets else writers[-1]["id"]
            selected_index = list(self.items).index(selected)
            self.selectionRequested.emit(selected_index)
        except Exception as failure:
            for sequence in sequences:
                sequence.deleteLater()
            message = qtTrId("listener.error.import").replace("%1", str(failure))
            logging.error(message)
            self.operationError.emit(message)
        if recording and selected_index >= 0:
            self.recordingImported.emit(selected_index)
        self.importFinished.emit(selected_index)

    @Slot(str, int, result=bool)
    def exportJson(self, filePath, currentIndex):
        if not 0 <= currentIndex < len(self.items):
            return False
        return self._startExport(filePath, [list(self.items)[currentIndex]])

    @Slot(str, result=bool)
    def exportJsonAll(self, filePath):
        return self._startExport(filePath, list(self.items))

    def _startExport(self, filePath, ids):
        if self.playbackBusy:
            self.operationError.emit(qtTrId("preset.io.busy"))
            return False
        try:
            presets, sequences = [], []
            for key in ids:
                item = self.items[key]
                if isinstance(item, WriterItem):
                    presets.append(item.exportSnapshot())
                else:
                    sequences.append({"id": key, "preset_name": item.presetName,
                                      "description": item.description, "sequence_steps": item.sequenceSteps})
            return self.presetIo.start("export", lambda progress, check:
                                       export_presets(filePath, presets, sequences, progress, check),
                                       self._exportDone)
        except Exception as error:
            self.operationError.emit(qtTrId("listener.error.export").replace("%1", str(error)))
            self.exportFinished.emit(False)
            return False

    def _exportDone(self, result, error):
        if error is not None:
            self.operationError.emit(qtTrId("listener.error.export").replace("%1", error))
        self.exportFinished.emit(error is None)

    def _exportJsonItem(self, currentIndex: int):
        if currentIndex < 0:
            return
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]

        if isinstance(item, SequenceItem):
            self.exportData["sequence_presets"].append({
                    "id": mId,
                    "preset_name": item.getPresetName(),
                    "description": item.getDescription(),
                    **sequence_fields(item.sequenceSteps)
                })
        if isinstance(item, WriterItem):
            messages = []
            for index in range(item.getDataTreeModelCount()):
                message = item.messageSnapshot(index)
                message["id"] = item.getDataItemId(index)
                message["name"] = item.getDataItemName(index)
                messages.append(message)
            self.exportData["presets"].append({
                    "id": mId,
                    "preset_name": item.getPresetName(),
                    "description": item.getDescription(),
                    "domain_id": item.getDomainId(),
                    "topic_name": item.getTopicName(),
                    "topic_type": item.getTopicType(),
                    "message": messages[0],
                    "messages": messages[1:],
                    "qos": item.qos
                })

    @Slot()
    def addSequence(self):
        if self.playbackBusy:
            return
        logging.info("Add Sequence pressed")
        self.beginResetModel()
        self.items[str(uuid.uuid4())] = SequenceItem(f"Sequence-{TesterModel.untitiledSequenceCount}")
        TesterModel.untitiledSequenceCount += 1
        self.endResetModel()
        self.countChanged.emit()

    @Slot(int)
    def duplicatePreset(self, currentIndex: int):
        if self.playbackBusy:
            return
        if currentIndex < 0 or currentIndex >= len(self.items.keys()):
            return
        logging.info(f"Duplicate preset at index {currentIndex}")
        mId = list(self.items.keys())[int(currentIndex)]
        item = self.items[mId]
        if isinstance(item, WriterItem):
            newId = str(uuid.uuid4())
            newPresetName = f"{item.getPresetName()}-copy"
            snapshot = item.exportSnapshot()
            messages = [dict(snapshot["messages"][index]) for index in range(item.getDataTreeModelCount())]
            duplicateDataItemIds = [newId] + [str(uuid.uuid4()) for _ in messages[1:]]
            prepared = {**snapshot, "id": newId, "preset_name": newPresetName, "messages": messages,
                        "ids": duplicateDataItemIds, "names": item.getDataItemNames()[:],
                        "index_by_id": {value: index for index, value in enumerate(duplicateDataItemIds)}}
            self.beginResetModel()
            self.items[newId] = WriterItem.fromImported(prepared, self._createDataTreeModel)
            self.endResetModel()
            self.countChanged.emit()
        elif isinstance(item, SequenceItem):
            newId = str(uuid.uuid4())
            newPresetName = f"{item.getPresetName()}-copy"
            self.beginResetModel()
            newSequenceItem = SequenceItem(newPresetName, item.getDescription())
            newSequenceItem.sequenceSteps = copy.deepcopy(item.sequenceSteps)
            self.items[newId] = newSequenceItem
            self.endResetModel()
            self.countChanged.emit()
