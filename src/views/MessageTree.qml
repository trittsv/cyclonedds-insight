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
import "qrc:/src/views/icons"
import org.eclipse.cyclonedds.insight

Column {
    id: tree
    property string payloadJson: ""
    property string scope: ""
    property string rootLabel: "root"
    property bool treeVisible: true
    readonly property bool hasWatches: fields.hasWatches
    readonly property bool hasPayload: fields.count > 0
    signal interactionStarted()
    width: parent.width

    function resetExpansion() {
        fields.collapseAll()
    }

    SampleTreeModel {
        id: fields
        payloadJson: tree.payloadJson
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
            required property bool pinned
            visible: tree.treeVisible || pinned
            width: tree.width
            spacing: 4

            Item { Layout.preferredWidth: Math.min(fieldRow.depth * 20, tree.width / 3) }
            Basic.ToolButton {
                id: fieldExpandButton
                objectName: "fieldExpand-" + fieldRow.index
                property bool longPressed: false
                hoverEnabled: true
                background: Rectangle {
                    radius: Constants.controlRadius
                    color: fieldExpandButton.hovered && fieldRow.expandable
                           ? Constants.cardBackgroundColor(rootWindow.isDarkMode)
                           : "transparent"
                    border.width: fieldExpandButton.visualFocus ? 1 : 0
                    border.color: Constants.accentColor
                }
                contentItem: Item {
                    ChevronIcon {
                        anchors.centerIn: parent
                        width: 14
                        height: 14
                        visible: fieldRow.expandable && !fieldRow.pinned
                        direction: fieldRow.expanded ? "down" : "right"
                        iconColor: Constants.mutedForegroundColor(rootWindow.isDarkMode)
                    }
                }
                enabled: fieldRow.expandable && !fieldRow.pinned
                implicitWidth: 24
                implicitHeight: 24
                Accessible.name: fieldRow.fieldLabel
                onPressed: {
                    tree.interactionStarted()
                    longPressed = false
                }
                onPressAndHold: {
                    longPressed = true
                    fields.expandAll()
                }
                onClicked: {
                    if (!longPressed)
                        fields.toggle(fieldRow.index)
                }
            }
            Label {
                text: (fieldRow.watched ? "★ " : "")
                      + (fieldRow.index === 0 ? tree.rootLabel : fieldRow.fieldLabel + ":")
                Layout.fillWidth: fieldRow.index === 0
                wrapMode: Text.Wrap
                font.bold: fieldRow.watched
                color: fieldRow.watched ? Constants.successColor
                                        : Constants.secondaryTextColor(rootWindow.isDarkMode)
                TapHandler {
                    enabled: fieldRow.expandable && !fieldRow.pinned
                    acceptedButtons: Qt.LeftButton
                    onTapped: {
                        tree.interactionStarted()
                        fields.toggle(fieldRow.index)
                    }
                }
                TapHandler {
                    acceptedButtons: Qt.RightButton
                    onTapped: {
                        tree.interactionStarted()
                        fieldMenu.popup()
                    }
                }
            }
            TextEdit {
                visible: fieldRow.index !== 0
                text: fieldRow.fieldValue
                font.bold: fieldRow.watched
                readOnly: true
                selectByMouse: true
                wrapMode: TextEdit.Wrap
                color: fieldRow.watched ? Constants.successColor
                                        : Constants.secondaryTextColor(rootWindow.isDarkMode)
                Layout.fillWidth: true
                onActiveFocusChanged: {
                    if (activeFocus)
                        tree.interactionStarted()
                }
                TapHandler {
                    acceptedButtons: Qt.RightButton
                    onTapped: {
                        tree.interactionStarted()
                        fieldMenu.popup()
                    }
                }
            }
            Menu {
                id: fieldMenu
                MenuItem {
                    text: fieldRow.watched ? qsTrId("listener.watch.remove") : qsTrId("listener.watch.add")
                    onTriggered: fields.toggleWatch(fieldRow.index)
                }
                MenuSeparator {}
                MenuItem {
                    objectName: "clearWatchlist-" + fieldRow.index
                    text: qsTrId("listener.watch.clear")
                    onTriggered: receiverModel.clearWatchlist()
                }
            }
        }
    }
}
