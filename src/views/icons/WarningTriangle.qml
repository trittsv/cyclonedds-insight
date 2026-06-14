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

import org.eclipse.cyclonedds.insight
import "qrc:/src/views"

Item {
    id: warningTriangle

    width: 15
    height: 15
    property bool showTooltip: false
    property bool enableTooltip: false
    property string tooltipText: ""
    property color warningColor: Constants.warningColor
    readonly property color symbolColor: rootWindow.isDarkMode
                                                 ? "#352709" : "#4a3506"

    Rectangle {
        anchors.centerIn: parent
        width: parent.width + 6
        height: parent.height + 6
        radius: Math.min(width, height) / 2
        visible: warningHover.containsMouse
        color: rootWindow.isDarkMode ? "#4a3b1d" : "#fff0c8"
        opacity: 0.75
    }

    Canvas {
        id: warningCanvas
        anchors.fill: parent
        antialiasing: true

        onPaint: {
            const context = getContext("2d")
            const inset = Math.max(1, Math.min(width, height) * 0.07)
            const bottom = height - inset

            context.clearRect(0, 0, width, height)
            context.beginPath()
            context.moveTo(width / 2, inset)
            context.lineTo(width - inset, bottom)
            context.lineTo(inset, bottom)
            context.closePath()
            context.lineJoin = "round"
            context.lineWidth = Math.max(1, Math.min(width, height) * 0.08)
            context.fillStyle = warningTriangle.warningColor
            context.fill()
            context.strokeStyle = rootWindow.isDarkMode
                                  ? "#f8cc72" : "#c88a12"
            context.stroke()
        }

        onWidthChanged: requestPaint()
        onHeightChanged: requestPaint()
    }

    Column {
        anchors.horizontalCenter: parent.horizontalCenter
        anchors.verticalCenter: parent.verticalCenter
        anchors.verticalCenterOffset: height * 0.06
        spacing: Math.max(1, warningTriangle.height * 0.05)

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.max(1.5, warningTriangle.width * 0.11)
            height: Math.max(4, warningTriangle.height * 0.34)
            radius: width / 2
            color: warningTriangle.symbolColor
        }

        Rectangle {
            anchors.horizontalCenter: parent.horizontalCenter
            width: Math.max(1.5, warningTriangle.width * 0.11)
            height: width
            radius: width / 2
            color: warningTriangle.symbolColor
        }
    }

    MouseArea {
        id: warningHover
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        cursorShape: warningTriangle.enableTooltip
                     ? Qt.WhatsThisCursor : Qt.ArrowCursor
        onEntered: warningTriangle.showTooltip = true
        onExited: warningTriangle.showTooltip = false
    }

    ToolTip {
        id: warningTriangleTooltip
        parent: warningTriangle
        visible: warningTriangle.showTooltip
                 && warningTriangle.enableTooltip
        delay: 300
        text: warningTriangle.tooltipText

        contentItem: Label {
            text: warningTriangleTooltip.text
            padding: 5
            color: rootWindow.isDarkMode ? "#eeeeee" : "#262626"
        }

        background: Rectangle {
            radius: 5
            border.width: 1
            border.color: Constants.borderColor(rootWindow.isDarkMode)
            color: Constants.cardBackgroundColor(rootWindow.isDarkMode)
        }
    }
}
