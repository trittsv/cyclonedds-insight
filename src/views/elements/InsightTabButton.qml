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

TabButton {
    id: control
    property alias tabText: label.text
    property bool showLeftSeparator: false

    leftInset: 0
    rightInset: 0
    topInset: 0
    bottomInset: 0
    leftPadding: 0
    rightPadding: 0
    topPadding: 0
    bottomPadding: 0

    background: Rectangle {
        id: tabBackground
        radius: 7
        color: control.checked
               ? rootWindow.isDarkMode
                 ? Constants.darkMainContent : Constants.lightMainContent
               : control.hovered
                 ? rootWindow.isDarkMode ? "#454545" : "#c9c7c7"
                 : rootWindow.isDarkMode ? "#383838" : "#dcdcdc"
        border.width: 1
        border.color: control.checked
                      ? rootWindow.isDarkMode ? "#555555" : "#d2d2d2"
                      : rootWindow.isDarkMode ? "#424242" : "#d8d8d8"

        Rectangle {
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            height: 7
            color: tabBackground.color
        }

        Rectangle {
            visible: control.showLeftSeparator
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.topMargin: 8
            anchors.bottomMargin: 8
            width: 1
            color: rootWindow.isDarkMode ? "#171717" : "#707070"
            z: 3
        }

        Rectangle {
            visible: control.checked
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.bottom: parent.bottom
            anchors.leftMargin: 1
            anchors.rightMargin: 1
            anchors.bottomMargin: -1
            height: 8
            color: parent.color
            z: 2
        }

        Rectangle {
            visible: control.checked
            anchors.left: parent.left
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.topMargin: 7
            width: 1
            color: tabBackground.border.color
            z: 3
        }

        Rectangle {
            visible: control.checked
            anchors.right: parent.right
            anchors.top: parent.top
            anchors.bottom: parent.bottom
            anchors.topMargin: 7
            width: 1
            color: tabBackground.border.color
            z: 3
        }

        Rectangle {
            anchors.top: parent.top
            anchors.left: parent.left
            anchors.right: parent.right
            anchors.leftMargin: 7
            anchors.rightMargin: 7
            anchors.topMargin: 1
            height: 3
            radius: 1
            color: "#274ff6"
            visible: control.checked
        }
    }

    contentItem: RowLayout {
        anchors.fill: parent
        anchors.margins: 0
        spacing: 0

        Label {
            id: label
            text: control.tabText
            font.pixelSize: 16
            font.bold: control.checked

            Layout.alignment: Qt.AlignVCenter | Qt.AlignLeft
            Layout.leftMargin: 16
        }
    }
}
