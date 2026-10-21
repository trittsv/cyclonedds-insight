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
import QtQuick.Layouts
import "qrc:/src/views/elements"

Rectangle {
    id: replay
    required property var session
    color: Constants.mainContentColor(rootWindow.isDarkMode)
    ColumnLayout {
        anchors.fill: parent
        anchors.margins: Constants.pageMargin
        spacing: 8
        Flow {
            Layout.fillWidth: true
            Layout.preferredHeight: implicitHeight
            spacing: 8
            Label { text: qsTrId("listener.replay.interval"); height: interval.height; verticalAlignment: Text.AlignVCenter }
            SpinBox { id: interval; from: 1; to: 60000; value: 100; enabled: !original.checked && !replay.session.playing; editable: true }
            CheckBox { id: original; text: qsTrId("listener.replay.original"); enabled: !replay.session.playing }
            Button {
                text: replay.session.playing ? qsTrId("listener.replay.stop") : qsTrId("listener.replay.play")
                enabled: replay.session.playing || replay.session.selectedRows.length > 0
                onClicked: {
                    if (replay.session.playing) replay.session.stop()
                    else replay.session.playSelected(original.checked, interval.value)
                }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            Button {
                text: qsTrId("listener.replay.select.all")
                enabled: !replay.session.playing
                onClicked: replay.session.selectAll(true)
            }
            Button {
                text: qsTrId("listener.replay.deselect.all")
                enabled: !replay.session.playing
                onClicked: replay.session.selectAll(false)
            }
            Label {
                text: qsTrId("listener.replay.selected.count").arg(replay.session.selectedRows.length).arg(replay.session.rows.length)
            }
            Item { Layout.fillWidth: true }
        }
        Label { text: qsTrId("listener.replay.position").arg(replay.session.position + 1).arg(replay.session.rows.length) }
        ListView {
            Layout.fillWidth: true
            Layout.fillHeight: true
            clip: true
            model: replay.session.rows
            spacing: 6
            delegate: Rectangle {
                id: messageRow
                objectName: "replayMessage-" + index
                required property int index
                required property var modelData
                readonly property bool selected: replay.session.selectedRows.indexOf(index) >= 0
                width: ListView.view.width
                height: messageContent.implicitHeight + 12
                radius: Constants.controlRadius
                color: selected ? Constants.cardBackgroundColor(rootWindow.isDarkMode) : "transparent"
                border.width: selected ? 1 : 0
                border.color: Constants.designBorderColor(rootWindow.isDarkMode)
                opacity: selected ? 1 : 0.55

                MouseArea {
                    anchors.fill: parent
                    enabled: !replay.session.playing
                    cursorShape: Qt.PointingHandCursor
                    onClicked: replay.session.setSelected(messageRow.index, !messageRow.selected)
                }
                RowLayout {
                    id: messageContent
                    anchors.left: parent.left
                    anchors.right: parent.right
                    anchors.margins: 6
                    y: 6
                    spacing: 8
                    CheckBox {
                        objectName: "replayMessageCheck-" + messageRow.index
                        checked: messageRow.selected
                        enabled: !replay.session.playing
                        Accessible.name: (messageRow.index + 1) + " · " + messageRow.modelData.topic
                        onClicked: replay.session.setSelected(messageRow.index, checked)
                    }
                    Label {
                        Layout.fillWidth: true
                        wrapMode: Text.Wrap
                        color: Constants.secondaryTextColor(rootWindow.isDarkMode)
                        text: (messageRow.index + 1) + " · " + messageRow.modelData.offset_ms.toFixed(1) + " ms · "
                              + messageRow.modelData.topic + "\n" + messageRow.modelData.text
                    }
                }
                Rectangle {
                    visible: replay.session.playing && messageRow.index === replay.session.position
                    anchors.left: parent.left
                    anchors.top: parent.top
                    anchors.bottom: parent.bottom
                    width: 3
                    radius: 1
                    color: Constants.accentColor
                }
            }
            ScrollBar.vertical: ScrollBar {}
        }
    }
}
