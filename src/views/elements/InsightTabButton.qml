/*
 * Copyright(c) 2024 Sven Trittler
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

import org.eclipse.cyclonedds.insight
import "qrc:/src/views"
import "qrc:/src/views/selection_details"

TabButton {
    id: control
    property alias tabText: label.text
    property string badgeKind: ""
    readonly property bool hasBadge: badgeKind.length > 0


    anchors.top: parent.top
    anchors.bottom: parent.bottom

    background: Rectangle {
        color: control.checked ? (rootWindow.isDarkMode ? Constants.darkMainContent : Constants.lightMainContent) : (control.hovered ? (rootWindow.isDarkMode ? "#454545" : "#c9c7c7") : (rootWindow.isDarkMode ? "#383838" : "#dcdcdc"))
        
        Rectangle {
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.right: parent.right
            width: 1
            color: rootWindow.isDarkMode ? "#1e1e1e" : "#b9b9b9"
        }

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            height: 3
            color: "#274ff6"
            visible: control.checked
        }
    }

    contentItem: RowLayout {
        anchors.fill: parent
        anchors.margins: 0
        spacing: control.hasBadge ? 7 : 0

        DetailBadge {
            visible: control.hasBadge
            kind: control.badgeKind
            Layout.preferredWidth: 20
            Layout.preferredHeight: 20
            Layout.leftMargin: 10
            Layout.alignment: Qt.AlignVCenter
        }

        Label {
            id: label
            text: control.tabText
            font.pixelSize: control.hasBadge ? 14 : 16
            font.bold: control.checked && control.hasBadge

            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            Layout.leftMargin: control.hasBadge ? 0 : 16
        }
    }
}
