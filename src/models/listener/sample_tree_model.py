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
        ("fieldLabel", "fieldValue", "depth", "expandable", "expanded", "watched", "pinned"), 1)}

    def __init__(self, parent=None):
        super().__init__(parent)
        self._payload = {}
        self._scope = ""
        self._watchStore = None
        self._expanded = set()
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

    @Property(bool, notify=changed)
    def hasWatches(self):
        return any(row["watched"] for row in self._rows)

    @Property(str, notify=changed)
    def payloadJson(self):
        return json.dumps(self._payload, ensure_ascii=False)

    @payloadJson.setter
    def payloadJson(self, value):
        # QVariantMap sorts dictionary keys on the Python/QML round trip.
        # Parse ordered JSON in Python to retain the tester tree's field order.
        self.payload = json.loads(value) if value else {}

    @Property("QVariantMap", notify=changed)
    def payload(self):
        return self._payload

    @payload.setter
    def payload(self, value):
        self._payload = value
        self._expanded.clear()
        self._rebuild()

    @Property(str, notify=changed)
    def scope(self):
        return self._scope

    @scope.setter
    def scope(self, value):
        if self._scope != value:
            self._expanded.clear()
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
        if 0 <= row < len(self._rows) and self._rows[row]["expandable"]:
            path = self._rows[row]["path"]
            if path in self._expanded:
                self._expanded.remove(path)
            else:
                self._expanded.add(path)
            self._rebuild()

    @staticmethod
    def _unwrap(value):
        while isinstance(value, dict) and list(value) == ["__value__"]:
            value = value["__value__"]
        return value

    @Slot()
    def expandAll(self):
        def walk(value, path):
            value = self._unwrap(value)
            if isinstance(value, (dict, list)) and value:
                self._expanded.add(path)
                entries = value.items() if isinstance(value, dict) else enumerate(value)
                for key, child in entries:
                    walk(child, path + (key,))

        walk(self._payload.get("root", {}), ())
        self._rebuild()

    @Slot()
    def collapseAll(self):
        if self._expanded:
            self._expanded.clear()
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
        pinned = []
        watch_ancestors = set()
        if self._watchStore is not None:
            for scope, path in self._watchStore.watches:
                if scope == self._scope:
                    watch_ancestors.update(path[:length] for length in range(len(path) + 1))

        def walk(value, label, path, ancestors):
            value = self._unwrap(value)
            container = isinstance(value, (dict, list))
            watched = self._isWatched(path)
            shown = all(p in self._expanded for p in ancestors)
            is_pinned = watched and bool(path)
            if shown or watched:
                row = {"path": path,
                       "fieldLabel": ".".join(map(str, path)) if is_pinned else label,
                       "fieldValue": ("{%d}" if isinstance(value, dict) else "[%d]") % len(value)
                       if container else ("" if value is None else json.dumps(value, ensure_ascii=False)),
                       "depth": 0 if is_pinned else len(path),
                       "expandable": container and bool(value),
                       "expanded": path in self._expanded, "watched": watched,
                       "pinned": is_pinned}
                (pinned if is_pinned else rows).append(row)
            if container and ((shown and path in self._expanded) or watched or path in watch_ancestors):
                entries = value.items() if isinstance(value, dict) else enumerate(value)
                for key, child in entries:
                    walk(child, str(key), path + (key,), ancestors + [path])
        if self._payload:
            walk(self._payload.get("root", {}), "root", (), [])
        # Keep watches immediately below the heading, with stable full paths
        # and indentation regardless of the expanded hierarchy below them.
        updated = rows[:1] + pinned + rows[1:]
        if [row["path"] for row in updated] == [row["path"] for row in self._rows]:
            previous = self._rows
            self._rows = updated
            for number, (old, new) in enumerate(zip(previous, updated)):
                roles = [role for role, name in self._roles.items()
                         if old[name.decode()] != new[name.decode()]]
                if roles:
                    index = self.index(number, 0)
                    self.dataChanged.emit(index, index, roles)
        else:
            self.beginResetModel()
            self._rows = updated
            self.endResetModel()
        self.changed.emit()
