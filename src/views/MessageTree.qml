/*
 * Copyright(c) 2026 Sven Trittler
 *
 * This program and the accompanying materials are made available under the
 * terms of the Eclipse Public License v. 2.0 which is available at
 * http://www.eclipse.org/legal/epl-2.0, or the Eclipse Distribution License
 * v. 1.0 which is available at
 * http://www.eclipse.org/org/documents/edl-v10.php.
 *
 * SPDX-License-Identifier: EPL-2.0 OR BSD-3-Clause
*/

import QtQuick
import QtQuick.Controls
import QtQuick.Controls.Basic as Basic
import QtQuick.Layouts
import org.eclipse.cyclonedds.insight

Column {
    id: tree
    property var payload: ({})
    property string scope: ""
    width: parent.width

    SampleTreeModel {
        id: fields
        payload: tree.payload
        scope: tree.scope
        watchStore: receiverModel
    }

    Repeater {
        model: fields
        delegate: RowLayout {
            id: fieldRow
            required property int index
            required property string fieldLabel
            required property string fieldValue
            required property int depth
            required property bool expandable
            required property bool expanded
            required property bool watched
            width: tree.width
            spacing: 4

            Item { Layout.preferredWidth: Math.min(fieldRow.depth * 16, tree.width / 3) }
            Basic.ToolButton {
                id: fieldExpandButton
                background: Item {}
                contentItem: Label {
                    text: fieldExpandButton.text
                    horizontalAlignment: Text.AlignHCenter
                    verticalAlignment: Text.AlignVCenter
                    color: Constants.secondaryTextColor(rootWindow.isDarkMode)
                }
                text: fieldRow.expandable ? (fieldRow.expanded ? "▾" : "▸") : "·"
                enabled: fieldRow.expandable
                implicitWidth: 26
                implicitHeight: 26
                onClicked: fields.toggle(fieldRow.index)
            }
            Label {
                text: (fieldRow.watched ? "★ " : "") + fieldRow.fieldLabel + ":"
                font.bold: fieldRow.watched
                color: Constants.secondaryTextColor(rootWindow.isDarkMode)
                TapHandler {
                    acceptedButtons: Qt.RightButton
                    onTapped: fieldMenu.popup()
                }
            }
            TextEdit {
                text: fieldRow.fieldValue
                font.bold: fieldRow.watched
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                color: Constants.secondaryTextColor(rootWindow.isDarkMode)
                Layout.fillWidth: true
                TapHandler {
                    acceptedButtons: Qt.RightButton
                    onTapped: fieldMenu.popup()
                }
            }
            Menu {
                id: fieldMenu
                MenuItem {
                    text: fieldRow.watched ? qsTrId("listener.watch.remove") : qsTrId("listener.watch.add")
                    onTriggered: fields.toggleWatch(fieldRow.index)
                }
            }
        }
    }
}
