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
from PySide6.QtCore import QAbstractListModel, QModelIndex, QObject, Property, Qt, Signal, Slot


class SampleTreeModel(QAbstractListModel):
    changed = Signal()
    _roles = {Qt.UserRole + i: name.encode() for i, name in enumerate(
        ("fieldLabel", "fieldValue", "depth", "expandable", "expanded", "watched"), 1)}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._payload = {}
        self._scope = ""
        self._watchStore = None
        self._expanded = {()}
        self._rows = []

    def roleNames(self):
        return self._roles

    def rowCount(self, parent=QModelIndex()):
        return 0 if parent.isValid() else len(self._rows)

    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and 0 <= index.row() < len(self._rows) and role in self._roles:
            return self._rows[index.row()][self._roles[role].decode()]
        return None

    @Property(int, notify=changed)
    def count(self):
        return len(self._rows)

    @Property("QVariantMap", notify=changed)
    def payload(self):
        return self._payload

    @payload.setter
    def payload(self, value):
        self._payload = value
        self._rebuild()

    @Property(str, notify=changed)
    def scope(self):
        return self._scope

    @scope.setter
    def scope(self, value):
        self._scope = value
        self._rebuild()

    @Property(QObject, notify=changed)
    def watchStore(self):
        return self._watchStore

    @watchStore.setter
    def watchStore(self, value):
        if self._watchStore is not None:
            self._watchStore.watchChanged.disconnect(self._rebuild)
        self._watchStore = value
        if value is not None:
            value.watchChanged.connect(self._rebuild)
        self._rebuild()

    @Slot(int)
    def toggle(self, row):
        if 0 <= row < len(self._rows):
            path = self._rows[row]["path"]
            if path in self._expanded:
                self._expanded.remove(path)
            else:
                self._expanded.add(path)
            self._rebuild()

    def _isWatched(self, path):
        if self._watchStore is None:
            return False
        # A more specific field rule overrides a rule on its parent.
        for length in range(len(path), -1, -1):
            key = (self._scope, path[:length])
            if key in self._watchStore.watchExclusions:
                return False
            if key in self._watchStore.watches:
                return True
        return False

    @Slot(int)
    def toggleWatch(self, row):
        if self._watchStore is not None and 0 <= row < len(self._rows):
            path = self._rows[row]["path"]
            watched = self._isWatched(path)
            for rules in (self._watchStore.watches, self._watchStore.watchExclusions):
                rules.difference_update({key for key in rules
                                         if key[0] == self._scope and key[1][:len(path)] == path})
            key = (self._scope, path)
            if watched:
                if self._isWatched(path):
                    self._watchStore.watchExclusions.add(key)
            else:
                self._watchStore.watches.add(key)
            self._watchStore.watchChanged.emit()

    @Slot()
    def _rebuild(self):
        rows = []

        def walk(value, label, path, ancestors):
            while isinstance(value, dict) and list(value) == ["__value__"]:
                value = value["__value__"]
            container = isinstance(value, (dict, list))
            watched = self._isWatched(path)
            shown = all(p in self._expanded for p in ancestors)
            if shown or watched:
                rows.append({"path": path, "fieldLabel": label if shown else ".".join(map(str, path)),
                             "fieldValue": ("{%d}" if isinstance(value, dict) else "[%d]") % len(value)
                             if container else json.dumps(value, ensure_ascii=False),
                             "depth": len(path) if shown else 0, "expandable": container and bool(value),
                             "expanded": path in self._expanded, "watched": watched})
            if container:
                entries = value.items() if isinstance(value, dict) else enumerate(value)
                for key, child in entries:
                    walk(child, str(key), path + (key,), ancestors + [path])
        if self._payload:
            walk(self._payload.get("root", {}), "root", (), [])
        self.beginResetModel()
        self._rows = rows
        self.endResetModel()
        self.changed.emit()
